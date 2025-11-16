#!/usr/bin/env bash
set -euo pipefail

RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

fail() {
  echo -e "${RED}[FAIL]${NC} $1"
  exit 1
}

pass() {
  echo -e "${GREEN}[PASS]${NC} $1"
}

info() {
  echo -e "${YELLOW}[INFO]${NC} $1"
}

ROOT_DIR="$(pwd)"

############# FRONTEND #############
info "Checking frontend/package.json for next, react, react-dom"
if [ ! -f "${ROOT_DIR}/frontend/package.json" ]; then
  fail "frontend/package.json not found"
fi

for dep in next react react-dom; do
  if ! grep -q "\"${dep}\"" "${ROOT_DIR}/frontend/package.json"; then
    fail "frontend/package.json missing dependency: ${dep}"
  fi
done
pass "frontend/package.json contains required deps"

cd "${ROOT_DIR}/frontend"

if [ ! -d node_modules ] || [ ! -d .next ]; then
  info "node_modules or .next missing — running npm ci"
  npm ci || fail "npm ci failed"
  pass "npm ci completed"
fi

info "Checking Next.js CLI"
if ! npx next --version >/dev/null 2>&1; then
  fail "npx next not available"
fi
pass "Next CLI available"

info "Building frontend"
npm run build || fail "npm run build failed"
if [ ! -d .next ]; then
  fail ".next not found after build"
fi
pass "Frontend built and .next exists"

info "Selecting free port for frontend (3000-3100)"
find_free_port() {
  for p in $(seq 3000 3100); do
    if ! lsof -iTCP:${p} -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo ${p}
      return 0
    fi
  done
  return 1
}

PORT=$(find_free_port) || fail "No free port found in range 3000-3100"
info "Starting frontend (background) on port ${PORT}"
npx next start -p ${PORT} &
FRONTEND_PID=$!
sleep 3
if ! lsof -iTCP:${PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
  kill ${FRONTEND_PID} >/dev/null 2>&1 || true
  fail "Frontend did not start on port ${PORT}"
fi
pass "Frontend started on port ${PORT} (PID ${FRONTEND_PID})"

############# BACKEND #############
info "Checking backend/requirements.txt for fastapi and uvicorn"
if [ ! -f "${ROOT_DIR}/backend/requirements.txt" ]; then
  fail "backend/requirements.txt not found"
fi
for pkg in fastapi uvicorn; do
  if ! grep -qi "^${pkg}" "${ROOT_DIR}/backend/requirements.txt" && ! grep -qi ",${pkg}" "${ROOT_DIR}/backend/requirements.txt"; then
    fail "backend/requirements.txt missing: ${pkg}"
  fi
done
pass "backend/requirements.txt contains fastapi and uvicorn"

cd "${ROOT_DIR}/backend"
info "Setting up virtualenv (if missing) at .venv"
if [ ! -d .venv ]; then
  python -m venv .venv || fail "python -m venv failed"
fi
source .venv/bin/activate
pip install --upgrade pip || fail "pip upgrade failed"
pip install -r requirements.txt || fail "pip install -r requirements.txt failed"
pass "Backend dependencies installed"

info "Starting backend (background) on port 8080"
nohup uvicorn app.main:app --host 127.0.0.1 --port 8080 >/tmp/uvicorn.log 2>&1 &
BACKEND_PID=$!
sleep 3
if ! lsof -iTCP:8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
  kill ${BACKEND_PID} || true
  tail -n +1 /tmp/uvicorn.log || true
  fail "Backend did not start on port 8080"
fi
pass "Backend started on port 8080 (PID ${BACKEND_PID})"

info "Checking backend /docs endpoint"
if ! curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/docs | grep -q "200"; then
  fail "Backend /docs did not return 200"
fi
pass "Backend /docs returned 200"

############# HEROKU INTEGRATION #############
cd "${ROOT_DIR}"
info "Checking Heroku CLI auth"
if ! command -v heroku >/dev/null 2>&1; then
  fail "Heroku CLI not installed"
fi
if ! heroku auth:whoami >/dev/null 2>&1; then
  fail "Heroku CLI not authenticated"
fi
pass "Heroku CLI installed and authenticated"

info "Checking git remote 'heroku'"
if ! git remote -v | grep -q "heroku"; then
  fail "git remote 'heroku' not configured"
fi
pass "Heroku git remote configured"

BRANCH=$(git branch --show-current || echo "master")
info "Detected branch: ${BRANCH}"

info "Pushing current branch to Heroku main"
git push heroku ${BRANCH}:main || fail "git push to heroku failed"
pass "Pushed branch ${BRANCH} to heroku main"

info "Tailing Heroku logs (10s)"
timeout 10s heroku logs --tail --app landtenmvp3 || true

############# PREBUILD CHECK #############
cd "${ROOT_DIR}/frontend"
if [ -d .next ]; then
  echo -e "${YELLOW}[INFO] Prebuilt frontend detected. Skipping build during deploy.${NC}"
else
  echo -e "${YELLOW}[INFO] No prebuilt frontend detected. Building now...${NC}"
  npm run build || fail "Frontend build failed during prebuild step"
fi

############# ENV CHECK #############
cd "${ROOT_DIR}"
info "Comparing local env files to Heroku config"
declare -a LOCAL_ENV_FILES=( ".env" ".env.local" )
MISSING=()
for f in "${LOCAL_ENV_FILES[@]}"; do
  if [ -f "${f}" ]; then
    while IFS='=' read -r key val; do
      if [[ -z "$key" || "$key" =~ ^# ]]; then
        continue
      fi
      if ! heroku config:get "$key" --app landtenmvp3 >/dev/null 2>&1; then
        MISSING+=("$key")
      fi
    done < "$f"
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  echo -e "${RED}[FAIL] Missing Heroku config vars:${NC} ${MISSING[*]}"
  exit 1
else
  pass "All local env vars present in Heroku config (where applicable)"
fi

echo -e "${GREEN}[PASS] Full stack verification completed successfully${NC}"

# Cleanup background processes
kill ${FRONTEND_PID} ${BACKEND_PID} >/dev/null 2>&1 || true
