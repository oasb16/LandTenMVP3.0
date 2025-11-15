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
npm run build
npm run start -p $PORT

trap 'kill $BACKEND_PID >/dev/null 2>&1 || true' EXIT
