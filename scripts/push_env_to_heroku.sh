#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${1:-}"
if [ -z "$APP_NAME" ]; then
  echo "❌ Usage: $0 <heroku-app-name>"
  exit 1
fi

# Always go to project root
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

# Check Heroku CLI
if ! command -v heroku &> /dev/null; then
  echo "❌ Heroku CLI not found. Install it from https://devcenter.heroku.com/articles/heroku-cli"
  exit 1
fi

echo "🔍 Scanning for .env files in project..."
ENV_FILES=$(find . -maxdepth 3 -type f -name ".env*" ! -name "*.example" 2>/dev/null | sort)

if [ -z "$ENV_FILES" ]; then
  echo "❌ No .env files found."
  exit 1
fi

echo "📁 Found env files:"
echo "$ENV_FILES" | while read -r f; do
  echo "   • $f"
done

TMP_FILE="$(mktemp)"
> "$TMP_FILE"

echo ""
echo "🔧 Merging environment variables..."
echo "$ENV_FILES" | while read -r file; do
  [ -z "$file" ] && continue
  grep -v '^\s*$' "$file" | grep -v '^\s*#' >> "$TMP_FILE" || true
done

# --- Portable reverse (macOS/Linux) ---
if command -v tac >/dev/null 2>&1; then
  REVERSE_CMD="tac"
else
  REVERSE_CMD="tail -r"
fi

# Deduplicate by keeping last occurrence of each key
DEDUP_FILE="$(mktemp)"
$REVERSE_CMD "$TMP_FILE" | awk -F= '!seen[$1]++' | $REVERSE_CMD > "$DEDUP_FILE"
mv "$DEDUP_FILE" "$TMP_FILE"

echo ""
echo "⚙️  Pushing config vars to Heroku app: $APP_NAME"
echo "-----------------------------------------"

while IFS='=' read -r key value; do
  key="$(echo "$key" | xargs)"
  value="$(echo "$value" | xargs)"
  [ -z "$key" ] && continue

  masked_value="$value"
  [[ "$key" =~ (KEY|SECRET|TOKEN|PASSWORD) ]] && masked_value="****"
  echo "→ Setting $key=$masked_value"
  heroku config:set "$key=$value" --app "$APP_NAME" >/dev/null || {
    echo "⚠️ Failed to set $key"
  }
done < "$TMP_FILE"

echo ""
echo "✅ All env vars uploaded successfully to Heroku app: $APP_NAME"
rm -f "$TMP_FILE"
echo "✨ Done!"
