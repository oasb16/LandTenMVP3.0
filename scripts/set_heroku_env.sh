#!/bin/bash
# Script to configure Heroku environment variables for contractor onboarding

echo "Setting FRONTEND_URL on Heroku..."

# Set the production frontend URL
heroku config:set FRONTEND_URL=https://land-ten-mvp-3-0.vercel.app -a landtenmvp3

echo "✓ Environment variable set!"
echo ""
echo "Verify with: heroku config:get FRONTEND_URL -a landtenmvp3"
