#!/usr/bin/env bash
set -euo pipefail

# Local bootstrap for LandTenMVP3.0
# - Prepares env files if missing
# - Optionally starts local DynamoDB via Docker and creates tables
# - Installs deps and launches backend (port 8080) and frontend (port 3000)

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

# 1) Ensure env files exist
copy_if_missing "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
copy_if_missing "$FRONTEND_DIR/.env.local.example" "$FRONTEND_DIR/.env.local"

# 2) Ask to run local DynamoDB (optional)
RUN_LOCAL_DDB=${RUN_LOCAL_DDB:-false}
if [ "$RUN_LOCAL_DDB" = "true" ]; then
  info "Starting local DynamoDB on port 8000 (Docker required)..."
  if ! command -v docker >/dev/null 2>&1; then
    err "Docker not found. Install/launch Docker Desktop or set RUN_LOCAL_DDB=false."
  else
    docker rm -f dynamodb-local >/dev/null 2>&1 || true
    docker run -d --name dynamodb-local -p 8000:8000 amazon/dynamodb-local:latest >/dev/null 2>&1 || true
    # wait for endpoint readiness (max 20s)
    export DYNAMO_ENDPOINT_URL="http://localhost:8000"
    export AWS_REGION="us-east-1"
    ATTEMPTS=0
    until curl -sSf "${DYNAMO_ENDPOINT_URL}" >/dev/null 2>&1 || [ $ATTEMPTS -gt 20 ]; do
      ATTEMPTS=$((ATTEMPTS+1))
      sleep 1
    done
    if [ $ATTEMPTS -gt 20 ]; then
      warn "DynamoDB local did not become ready on ${DYNAMO_ENDPOINT_URL}. Skipping table creation."
    else
      info "Creating tables (chat_messages, incidents, jobs)..."
      # ensure boto3 available in a tiny temp venv so system Python needn't have it
      TMPVENV="${ROOT_DIR}/.ddb-venv"
      python3 -m venv "$TMPVENV" >/dev/null 2>&1 || true
      source "$TMPVENV/bin/activate"
      pip install -q boto3 >/dev/null 2>&1 || true
      python - <<'PY'
import os,boto3
endpoint=os.getenv('DYNAMO_ENDPOINT_URL')
region=os.getenv('AWS_REGION','us-east-1')
prefix=os.getenv('TABLE_PREFIX','landtenmvp')
stage=os.getenv('STAGE','dev')
def name(b):
    return f"{prefix}_{stage}_{b}"
ddb=boto3.client('dynamodb',region_name=region,endpoint_url=endpoint)
def create_chat():
    try:
        ddb.create_table(
            TableName=name('chat_messages'),
            KeySchema=[{'AttributeName':'thread_id','KeyType':'HASH'},{'AttributeName':'timestamp','KeyType':'RANGE'}],
            AttributeDefinitions=[{'AttributeName':'thread_id','AttributeType':'S'},{'AttributeName':'timestamp','AttributeType':'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
    except ddb.exceptions.ResourceInUseException:
        pass
def create_incidents():
    try:
        ddb.create_table(
            TableName=name('incidents'),
            KeySchema=[{'AttributeName':'user_id','KeyType':'HASH'}],
            AttributeDefinitions=[{'AttributeName':'user_id','AttributeType':'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
    except ddb.exceptions.ResourceInUseException:
        pass
def create_jobs():
    try:
        ddb.create_table(
            TableName=name('jobs'),
            KeySchema=[{'AttributeName':'user_id','KeyType':'HASH'}],
            AttributeDefinitions=[{'AttributeName':'user_id','AttributeType':'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
    except ddb.exceptions.ResourceInUseException:
        pass
create_chat(); create_incidents(); create_jobs(); print('Tables ready')
PY
      deactivate || true
    fi
  fi
else
  warn "RUN_LOCAL_DDB=false. Chat history will fall back to in-memory if DynamoDB not reachable."
fi

# 3) Backend: create venv, install deps, start server
info "Setting up backend environment..."
cd "$BACKEND_DIR"
python3 -m venv .venv >/dev/null 2>&1 || true
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

# Ensure dev auth bypass for local unless explicitly disabled
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

# 4) Frontend: install and start dev server
info "Setting up frontend..."
cd "$FRONTEND_DIR"
# Clean Next.js cache to avoid stale module errors
rm -rf .next >/dev/null 2>&1 || true
npm install >/dev/null 2>&1 || npm ci >/dev/null 2>&1 || true
export NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL:-http://localhost:8080}
info "Starting frontend on http://localhost:3000 ..."
(
  npm run dev
) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID >/dev/null 2>&1 || true' INT TERM EXIT

wait
