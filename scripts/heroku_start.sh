#!/usr/bin/env bash
set -euo pipefail

echo "[INFO] Heroku detected — launching backend + frontend"

# ------------------------------
# Backend (FastAPI / Uvicorn)
# ------------------------------
if [ -d "backend" ]; then
  echo "[INFO] Installing backend dependencies..."
  cd backend
  pip install --upgrade pip
  pip install -r requirements.txt

  echo "[INFO] Starting backend on port 8080..."
  nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 > ../backend.log 2>&1 &

  cd ..
else
  echo "[WARN] Backend folder not found — skipping backend startup."
fi

# ------------------------------
# Frontend (Next.js)
# ------------------------------
if [ -d "frontend" ]; then
  cd frontend
  echo "[INFO] Installing frontend dependencies..."
  npm ci --omit=dev

  echo "[INFO] Building frontend..."
  NODE_OPTIONS="--max-old-space-size=256" npm run build

  echo "[INFO] Starting frontend on port ${PORT:-3000}..."
  exec npx next start -p "${PORT:-3000}"
else
  echo "[ERROR] Frontend folder not found. Exiting."
  exit 1
fi
