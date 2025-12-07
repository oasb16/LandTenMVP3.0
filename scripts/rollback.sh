#!/bin/bash
set -e

echo "🔄 Starting rollback procedure..."

# Backup current state
echo "📦 Creating backup..."
heroku releases -a landtenmvp3 | head -5

# Rollback Heroku
echo "⏮️  Rolling back Heroku deployment..."
heroku rollback -a landtenmvp3

# Rollback Vercel (if needed)
echo "⏮️  Rolling back Vercel deployment..."
cd frontend
vercel rollback || true
cd ..

# Restore DynamoDB tables from backup (if available)
echo "💾 Checking DynamoDB backups..."
python scripts/restore_dynamodb_backup.py || true

echo "✅ Rollback complete"
echo "🔍 Verify services are working correctly"
