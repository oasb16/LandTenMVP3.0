#!/usr/bin/env bash
set -euo pipefail

# Local bootstrap for LandTenMVP3.0
# - Uses dual ngrok accounts for distinct backend/frontend tunnels
# - Auto-injects live URLs into .env.local
# - Optionally runs local DynamoDB (RUN_LOCAL_DDB=true)
# - Launches backend (FastAPI 8080) and frontend (Next.js 3000)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

info() { echo -e "[INFO] $*"; }
warn() { echo -e "[WARN] $*"; }
err()  { echo -e "[ERR ] $*" >&2; }

copy_if_missing() {
  local src="$1" dst="$2"
  if [ ! -f "$dst" ]; then
    cp "$src" "$dst" || true
    info "Created $dst from template. Please review values."
  fi
}

# ---------------------------------------------------------------------------
# 1) Ensure env files exist
# ---------------------------------------------------------------------------
copy_if_missing "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
copy_if_missing "$FRONTEND_DIR/.env.local.example" "$FRONTEND_DIR/.env.local"

# ---------------------------------------------------------------------------
# 2) Dual ngrok setup (two accounts => two unique tunnels)
# ---------------------------------------------------------------------------
info "Starting dual ngrok tunnels for backend (8080) and frontend (3000)..."

NGROK_LOG_DIR="$ROOT_DIR/.ngrok"
mkdir -p "$NGROK_LOG_DIR"
chmod 755 "$NGROK_LOG_DIR"
rm -f "$NGROK_LOG_DIR"/*.log >/dev/null 2>&1 || true

# Load tokens from env
if [ -f "$FRONTEND_DIR/.env.local" ]; then
  set -a
  source "$FRONTEND_DIR/.env.local"
  set +a
fi

if [[ -z "${NGROK_AUTHTOKEN_BACKEND:-}" || -z "${NGROK_AUTHTOKEN_FRONTEND:-}" ]]; then
  err "Missing ngrok tokens. Please set NGROK_AUTHTOKEN_BACKEND and NGROK_AUTHTOKEN_FRONTEND in .env.local"
  exit 1
fi

# Separate config files per account
FRONTEND_CONFIG="$NGROK_LOG_DIR/frontend.yml"
BACKEND_CONFIG="$NGROK_LOG_DIR/backend.yml"

cat > "$FRONTEND_CONFIG" <<YAML
version: 3
agent:
  authtoken: ${NGROK_AUTHTOKEN_FRONTEND}
  log_level: info
  log_format: logfmt
YAML

cat > "$BACKEND_CONFIG" <<YAML
version: 3
agent:
  authtoken: ${NGROK_AUTHTOKEN_BACKEND}
  log_level: info
  log_format: logfmt
YAML

# Kill any old ngrok processes
pkill -f "ngrok http" >/dev/null 2>&1 || true
sleep 1

# Start backend tunnel (US region)
ngrok http 8080 --config="$BACKEND_CONFIG" --region=us --log=stdout --log-format=logfmt >"$NGROK_LOG_DIR/backend.log" 2>&1 &
BACKEND_NGROK_PID=$!

# Start frontend tunnel (EU region)
ngrok http 3000 --config="$FRONTEND_CONFIG" --region=eu --log=stdout --log-format=logfmt >"$NGROK_LOG_DIR/frontend.log" 2>&1 &
FRONTEND_NGROK_PID=$!

sleep 6

BACKEND_URL=$(grep -m1 -Eo "https://[a-zA-Z0-9-]+\.ngrok[-free]*\.dev" "$NGROK_LOG_DIR/backend.log" | head -1 || true)
FRONTEND_URL=$(grep -m1 -Eo "https://[a-zA-Z0-9-]+\.ngrok[-free]*\.dev" "$NGROK_LOG_DIR/frontend.log" | head -1 || true)

if [[ -z "$BACKEND_URL" || -z "$FRONTEND_URL" ]]; then
  err "Failed to detect ngrok tunnels. Check internet connection or ngrok tokens."
  exit 1
fi

export NEXTAUTH_URL="$FRONTEND_URL"
export NEXT_PUBLIC_BACKEND_URL="${BACKEND_URL}/api"
export BACKEND_URL="$BACKEND_URL"
export BACKEND_INTERNAL_URL="$BACKEND_URL"

# Auto-update backend .env webhook
if grep -q "^STREAM_WEBHOOK_URL=" "$BACKEND_DIR/.env"; then
  sed -i '' "s|^STREAM_WEBHOOK_URL=.*|STREAM_WEBHOOK_URL=${BACKEND_URL}/ai/stream-webhook|" "$BACKEND_DIR/.env"
else
  echo "STREAM_WEBHOOK_URL=${BACKEND_URL}/ai/stream-webhook" >> "$BACKEND_DIR/.env"
fi

info "Frontend tunnel: $FRONTEND_URL"
info "Backend tunnel:  $BACKEND_URL"
info "Using NEXTAUTH_URL=$NEXTAUTH_URL"
info "Using NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL"

# ---------------------------------------------------------------------------
# 3) Sync .env.local with live URLs
# ---------------------------------------------------------------------------
if grep -q "^NEXTAUTH_URL=" "$FRONTEND_DIR/.env.local"; then
  sed -i '' "s|^NEXTAUTH_URL=.*|NEXTAUTH_URL=$NEXTAUTH_URL|" "$FRONTEND_DIR/.env.local"
else
  echo "NEXTAUTH_URL=$NEXTAUTH_URL" >> "$FRONTEND_DIR/.env.local"
fi

if grep -q "^NEXT_PUBLIC_BACKEND_URL=" "$FRONTEND_DIR/.env.local"; then
  sed -i '' "s|^NEXT_PUBLIC_BACKEND_URL=.*|NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL|" "$FRONTEND_DIR/.env.local"
else
  echo "NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL" >> "$FRONTEND_DIR/.env.local"
fi

# ---------------------------------------------------------------------------
# 4) Optional local DynamoDB
# ---------------------------------------------------------------------------
RUN_LOCAL_DDB=${RUN_LOCAL_DDB:-false}
if [ "$RUN_LOCAL_DDB" = "true" ]; then
  info "Starting local DynamoDB on port 8000 (Docker required)..."
  if ! command -v docker >/dev/null 2>&1; then
    err "Docker not found. Install Docker Desktop or set RUN_LOCAL_DDB=false."
  else
    docker rm -f dynamodb-local >/dev/null 2>&1 || true
    docker run -d --name dynamodb-local -p 8000:8000 amazon/dynamodb-local:latest >/dev/null 2>&1 || true
    export DYNAMO_ENDPOINT_URL="http://localhost:8000"
    export AWS_REGION="us-east-1"
  fi
else
  warn "RUN_LOCAL_DDB=false. Chat history will fall back to in-memory if DynamoDB not reachable."
fi

# ---------------------------------------------------------------------------
# 5) Start backend
# ---------------------------------------------------------------------------
info "Setting up backend environment..."
cd "$BACKEND_DIR"
python3 -m venv .venv >/dev/null 2>&1 || true
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null
export AUTH_DISABLED=${AUTH_DISABLED:-true}
export AWS_REGION=${AWS_REGION:-us-east-1}
export PYTHONPATH="$BACKEND_DIR${PYTHONPATH:+:$PYTHONPATH}"

UVICORN_BIN="$BACKEND_DIR/.venv/bin/uvicorn"
if [ ! -x "$UVICORN_BIN" ]; then
  err "Expected uvicorn at $UVICORN_BIN but it is missing or not executable."
  exit 1
fi

info "Starting backend on http://localhost:8080 ..."
(
  "$UVICORN_BIN" app.main:app --host 0.0.0.0 --port 8080 --reload
) &
BACKEND_PID=$!

# ---------------------------------------------------------------------------
# 6) Start frontend
# ---------------------------------------------------------------------------
info "Setting up frontend..."
cd "$FRONTEND_DIR"
rm -rf .next >/dev/null 2>&1 || true
npm install >/dev/null 2>&1 || npm ci >/dev/null 2>&1 || true

info "Starting frontend on $NEXTAUTH_URL ..."
(
  npm run dev
) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID >/dev/null 2>&1 || true' INT TERM EXIT
wait
