#!/usr/bin/env bash
set -euo pipefail

# Usage: IMAGE_URI=xxx ENV_FILE=/path/to/backend.env ./scripts/deploy_ec2.sh

if [ -z "${IMAGE_URI:-}" ]; then echo "IMAGE_URI required"; exit 1; fi
if [ -z "${ENV_FILE:-}" ]; then echo "ENV_FILE required"; exit 1; fi

CONTAINER_NAME=landten-backend
PORT=${PORT:-8080}

docker pull "$IMAGE_URI"
docker rm -f $CONTAINER_NAME >/dev/null 2>&1 || true
docker run -d --name $CONTAINER_NAME --restart unless-stopped \
  --env-file "$ENV_FILE" -p $PORT:8080 "$IMAGE_URI"
echo "Deployed $CONTAINER_NAME -> $IMAGE_URI on port $PORT"
