# Deployment Guide

This guide explains how to deploy the LandTen MVP 3.0 application to Heroku using GitHub Actions.

## Prerequisites

1. A Heroku account (sign up at https://signup.heroku.com/)
2. A Heroku app created for this project
3. Access to your GitHub repository settings

## Setup Instructions

### Step 1: Get Your Heroku Credentials

1. **Heroku API Key:**
   - Go to https://dashboard.heroku.com/account
   - Scroll down to "API Key" section
   - Click "Reveal" to see your API key
   - Copy this key (it looks like: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)

2. **Heroku App Name:**
   - Go to https://dashboard.heroku.com/apps
   - Find your app name (e.g., `my-landten-app`)
   - If you don't have an app yet, create one by clicking "New" → "Create new app"

3. **Heroku Email:**
   - The email address associated with your Heroku account

### Step 2: Add GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add the following three secrets:

   | Secret Name | Value | Example |
   |-------------|-------|---------|
   | `HEROKU_API_KEY` | Your Heroku API key | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
   | `HEROKU_APP_NAME` | Your Heroku app name | `my-landten-app` |
   | `HEROKU_EMAIL` | Your Heroku email | `you@example.com` |

### Step 3: Deploy

The deployment happens automatically when you:
- Push to the `main` or `master` branch
- Manually trigger the workflow from GitHub Actions tab

#### Automatic Deployment (Recommended)
```bash
git push origin main
```

#### Manual Deployment
1. Go to your GitHub repository
2. Click **Actions** tab
3. Select **Deploy to Heroku** workflow
4. Click **Run workflow** → **Run workflow**

### Step 4: Verify Deployment

After the workflow completes:
1. Check the Actions tab for success ✅
2. Visit your app: `https://YOUR_APP_NAME.herokuapp.com`
3. Check Heroku logs if needed:
   ```bash
   heroku logs --tail --app YOUR_APP_NAME
   ```

## Deployment Architecture

This application is deployed as a monorepo to Heroku:

- **Frontend (Next.js):** Runs on port specified by Heroku's `$PORT` variable
- **Backend (FastAPI):** Runs on port 8080
- **Build Process:** Uses the Procfile and heroku-postbuild script in package.json

### Environment Variables

Make sure to configure the following environment variables in Heroku:

#### Required Variables
```bash
# Stream Chat
STREAM_CHAT_API_KEY=your_stream_api_key
STREAM_CHAT_API_SECRET=your_stream_api_secret
STREAM_WEBHOOK_SECRET=your_webhook_secret

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# OpenAI
OPENAI_API_KEY=sk-your_openai_key

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# NextAuth
NEXTAUTH_URL=https://YOUR_APP_NAME.herokuapp.com
NEXTAUTH_SECRET=your_nextauth_secret

# Stripe
STRIPE_SECRET_KEY=sk_test_your_stripe_key
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
```

#### Optional Variables
```bash
# Backend URL (if separate)
BACKEND_INTERNAL_URL=http://localhost:8080
NEXT_PUBLIC_BACKEND_URL=https://YOUR_APP_NAME.herokuapp.com

# OpenAI Configuration
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.3

# DynamoDB
DYNAMODB_TABLE_PREFIX=landten_

# Auth (Development Only)
AUTH_DISABLED=false
```

### Setting Environment Variables

You can set environment variables using:

1. **Heroku Dashboard:**
   - Go to https://dashboard.heroku.com/apps/YOUR_APP_NAME/settings
   - Click "Reveal Config Vars"
   - Add each variable

2. **Heroku CLI:**
   ```bash
   heroku config:set VARIABLE_NAME=value --app YOUR_APP_NAME
   ```

3. **Automated Script:**
   ```bash
   ./scripts/push_env_to_heroku.sh YOUR_APP_NAME
   ```

## Troubleshooting

### Deployment Fails
1. Check GitHub Actions logs for errors
2. Verify all three secrets are set correctly
3. Ensure your Heroku app exists
4. Check that your API key is valid

### App Crashes After Deployment
1. Check Heroku logs:
   ```bash
   heroku logs --tail --app YOUR_APP_NAME
   ```
2. Verify all environment variables are set
3. Check that dependencies are correctly specified in package.json and requirements.txt

### Build Fails
1. Ensure frontend builds locally: `cd frontend && npm run build`
2. Ensure backend dependencies install: `cd backend && pip install -r requirements.txt`
3. Check Node.js and Python versions match Heroku requirements

## Additional Resources

- [Heroku Documentation](https://devcenter.heroku.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

## Support

For issues related to:
- **Deployment:** Check GitHub Actions logs and Heroku logs
- **Application:** See [README.md](./README.md) and documentation in `/docs`
- **Environment Setup:** See [backend/.env.example](./backend/.env.example) and [frontend/.env.example](./frontend/.env.example)
