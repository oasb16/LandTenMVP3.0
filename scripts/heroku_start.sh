#!/usr/bin/env bash
set -e

echo "[INFO] Heroku detected — launching backend + frontend"

#!/usr/bin/env bash
set -e

echo "[INFO] Heroku detected — launching backend + frontend"

# ensure python + pip available
if ! command -v pip &> /dev/null; then
  echo "[ERROR] pip not found. Check Heroku buildpacks order."
  exit 1
fi

# backend
if [ -d "backend" ]; then
  cd backend
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  echo "[INFO] Starting backend on port 8080..."
  nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 &
  cd ..
else
  echo "[WARN] Backend folder not found."
fi

# frontend
cd frontend
echo "[INFO] Installing frontend dependencies..."
npm ci --omit=dev
echo "[INFO] Building frontend..."
npm run build

# reduce memory usage for Heroku
export NODE_OPTIONS="--max-old-space-size=256"

echo "[INFO] Starting frontend on port $PORT..."
npx next start -p "$PORT"
#!/usr/bin/env bash
set -e

echo "[INFO] Heroku detected — launching backend + frontend"

# Backend setup
if [ -d "backend" ]; then
  cd backend
  if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python -m venv .venv
  fi
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  echo "[INFO] Starting backend on port 8080..."
  nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 &
  cd ..
else
  echo "[WARN] Backend folder not found, skipping backend startup."
fi

# Frontend build
cd frontend
npm install --omit=dev
npm run build

# Reduce memory usage
export NODE_OPTIONS="--max-old-space-size=256"

# Serve frontend
echo "[INFO] Starting frontend on port $PORT..."
npx next start -p "$PORT"
#!/usr/bin/env bash
set -e

echo "[INFO] Heroku detected — launching backend + frontend"

# Start backend
cd backend
nohup uvicorn app.main:app --host 0.0.0.0 --port=8080 &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm install --omit=dev --no-audit --prefer-offline
npm ci --include=dev
npm run build
npm run start -p $PORT

trap 'kill $BACKEND_PID >/dev/null 2>&1 || true' EXIT
