#!/usr/bin/env bash
set -e

echo "[INFO] Heroku detected — launching backend + frontend"

# backend
if [ -d "backend" ]; then
  cd backend
  echo "[INFO] Installing backend dependencies..."
  pip install --upgrade pip
  pip install -r requirements.txt
  echo "[INFO] Starting backend on port 8080..."
  nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 &
  cd ..
else
  echo "[WARN] Backend folder not found, skipping backend startup."
fi

# frontend
cd frontend
echo "[INFO] Installing frontend dependencies..."
npm ci --omit=dev

echo "[INFO] Building frontend..."
npm run build

export NODE_OPTIONS="--max-old-space-size=256"

echo "[INFO] Starting frontend on port $PORT..."
npx next start -p "$PORT"
