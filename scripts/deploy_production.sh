#!/bin/bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}$1${NC}"; }
fail() { echo -e "${RED}$1${NC}"; exit 1; }

log "🚀 Starting Production Deployment"

# Step 1: Validate environment
log "📋 Step 1: Validating environment variables..."
python scripts/validate_env.py || fail "❌ Environment validation failed"
log "✅ Environment validated"

if [ -z "${HEROKU_API_KEY:-}" ]; then
  fail "❌ HEROKU_API_KEY is required to deploy backend"
fi

if [ -z "${VERCEL_TOKEN:-}" ]; then
  fail "❌ VERCEL_TOKEN is required to deploy frontend"
fi

# Step 2: Setup AWS infrastructure
log "☁️  Step 2: Setting up AWS infrastructure..."
python scripts/setup_production.py || fail "❌ AWS setup failed"
log "✅ AWS infrastructure ready"

# Step 3: Deploy backend to Heroku
log "🔧 Step 3: Deploying backend to Heroku..."
cd backend
if git remote get-url heroku >/dev/null 2>&1; then
  true
else
  git remote add heroku https://heroku:${HEROKU_API_KEY:-}@git.heroku.com/landtenmvp3.git
fi
HUSKY=0 git push heroku HEAD:main
heroku ps:scale web=1 -a landtenmvp3
cd ..
log "✅ Backend deployed"

# Step 4: Deploy frontend to Vercel
log "🎨 Step 4: Deploying frontend to Vercel..."
cd frontend
vercel --prod --yes --token="${VERCEL_TOKEN}"
cd ..
log "✅ Frontend deployed"

# Step 5: Setup Stripe webhooks
log "💳 Step 5: Configuring Stripe webhooks..."
python scripts/setup_stripe_webhook.py || fail "❌ Stripe webhook setup failed"
log "✅ Stripe webhooks configured"

# Step 6: Health checks
log "🏥 Step 6: Running health checks..."
curl -f https://landtenmvp3-55ce0053f28a.herokuapp.com/health >/dev/null
curl -f https://land-ten-mvp-3-0.vercel.app >/dev/null
log "✅ All services healthy"

# Step 7: Test workflow
log "🧪 Step 7: Testing production workflow..."
python scripts/test_production_flow.py || fail "❌ Production tests failed"
log "✅ Production tests passed"

log "\n🎉 DEPLOYMENT COMPLETE!"
echo "📊 Production URLs:"
echo "   Frontend: https://land-ten-mvp-3-0.vercel.app"
echo "   Backend:  https://landtenmvp3-55ce0053f28a.herokuapp.com"
echo "   API Docs: https://landtenmvp3-55ce0053f28a.herokuapp.com/api/docs"
echo ""
echo "🔍 Next Steps:"
echo "   1. Test complete workflow in browser"
echo "   2. Verify Stripe webhook in dashboard"
echo "   3. Monitor logs for any errors"
echo "   4. Set up monitoring alerts"
