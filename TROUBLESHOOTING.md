# LandTen MVP 3.0 - Troubleshooting Guide

This guide helps diagnose and fix common issues encountered during development, testing, and deployment.

## Table of Contents

1. [Setup Issues](#setup-issues)
2. [Backend Issues](#backend-issues)
3. [Frontend Issues](#frontend-issues)
4. [Database Issues](#database-issues)
5. [File Upload Issues](#file-upload-issues)
6. [Payment Issues](#payment-issues)
7. [Webhook Issues](#webhook-issues)
8. [Docker Issues](#docker-issues)
9. [Deployment Issues](#deployment-issues)

---

## Setup Issues

### Problem: `./scripts/setup_all.sh` fails with "command not found"

**Symptoms:**
```bash
./scripts/setup_all.sh: command not found
```

**Solution:**
```bash
# Make the script executable
chmod +x scripts/setup_all.sh

# Then run it
./scripts/setup_all.sh
```

### Problem: Python dependencies fail to install

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**Solutions:**
1. Check Python version (must be 3.10+):
   ```bash
   python3 --version
   ```

2. Upgrade pip:
   ```bash
   pip install --upgrade pip
   ```

3. Use virtual environment:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

### Problem: npm install fails

**Symptoms:**
```
npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree
```

**Solutions:**
1. Clear npm cache:
   ```bash
   npm cache clean --force
   ```

2. Delete node_modules and reinstall:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

3. Use legacy peer deps:
   ```bash
   npm install --legacy-peer-deps
   ```

---

## Backend Issues

### Problem: Backend won't start - "Module not found"

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

### Problem: Backend crashes on startup with AWS credentials error

**Symptoms:**
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solutions:**
1. Check environment variables:
   ```bash
   echo $AWS_ACCESS_KEY_ID
   echo $AWS_SECRET_ACCESS_KEY
   ```

2. Set credentials in `.env`:
   ```bash
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-1
   ```

3. For local development, use LocalStack:
   ```bash
   DYNAMODB_ENDPOINT=http://localhost:4566
   S3_ENDPOINT=http://localhost:4566
   ```

### Problem: Import errors from `app.routes`

**Symptoms:**
```
ImportError: cannot import name 'incidents' from 'app.routes'
```

**Solution:**
1. Check that all route files exist:
   ```bash
   ls backend/app/routes/
   ```

2. Verify `__init__.py` exists in routes directory:
   ```bash
   touch backend/app/routes/__init__.py
   ```

3. Check for circular imports in route files

### Problem: CORS errors when calling backend from frontend

**Symptoms:**
```
Access to fetch at 'http://localhost:8000/api/v1/...' from origin 'http://localhost:3000'
has been blocked by CORS policy
```

**Solution:**
1. Check CORS configuration in `backend/app/main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. Verify `BACKEND_CORS_ORIGINS` in `.env`:
   ```bash
   BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8000
   ```

---

## Frontend Issues

### Problem: Frontend won't build - "Module not found"

**Symptoms:**
```
Module not found: Can't resolve '@/components/...'
```

**Solutions:**
1. Check `tsconfig.json` paths configuration
2. Verify file exists at the import path
3. Restart Next.js dev server:
   ```bash
   npm run dev
   ```

### Problem: API calls return 404

**Symptoms:**
Frontend makes requests but gets 404 errors

**Solutions:**
1. Check `next.config.js` rewrites:
   ```javascript
   async rewrites() {
     return [
       {
         source: '/api/v1/:path*',
         destination: 'http://localhost:8000/api/v1/:path*',
       },
     ];
   }
   ```

2. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

3. Check environment variables:
   ```bash
   cat frontend/.env.local | grep BACKEND_URL
   ```

### Problem: Stripe Elements not loading

**Symptoms:**
Payment form shows blank or error

**Solutions:**
1. Verify Stripe publishable key in `.env.local`:
   ```bash
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```

2. Check browser console for Stripe errors

3. Ensure Stripe script loaded in layout/page

---

## Database Issues

### Problem: DynamoDB table does not exist

**Symptoms:**
```
ResourceNotFoundException: Requested resource not found
```

**Solutions:**
1. Create tables:
   ```bash
   python3 scripts/create_dynamodb_tables.py
   ```

2. For local development:
   ```bash
   python3 scripts/create_dynamodb_tables.py --local
   ```

3. Check table exists:
   ```bash
   aws dynamodb list-tables --endpoint-url http://localhost:8000
   ```

### Problem: Cannot connect to DynamoDB

**Symptoms:**
```
botocore.exceptions.EndpointConnectionError: Could not connect to the endpoint URL
```

**Solutions:**
1. Check endpoint configuration in `.env`:
   ```bash
   # For local:
   DYNAMODB_ENDPOINT=http://localhost:8000

   # For AWS:
   # Leave empty or remove DYNAMODB_ENDPOINT
   ```

2. For LocalStack, ensure it's running:
   ```bash
   docker ps | grep localstack
   ```

3. Start LocalStack:
   ```bash
   docker-compose up localstack
   ```

### Problem: GSI query fails

**Symptoms:**
```
ValidationException: The table does not have the specified index
```

**Solutions:**
1. Verify index exists:
   ```bash
   aws dynamodb describe-table --table-name landten_dev_incidents
   ```

2. Recreate tables with indexes:
   ```bash
   python3 scripts/create_dynamodb_tables.py --stage dev
   ```

---

## File Upload Issues

### Problem: Photo upload fails with CORS error

**Symptoms:**
```
Access to XMLHttpRequest at 'https://s3.amazonaws.com/...' has been blocked by CORS policy
```

**Solutions:**
1. Apply CORS configuration to S3 bucket:
   ```bash
   aws s3api put-bucket-cors \
     --bucket landten-incident-photos \
     --cors-configuration file://scripts/s3-cors.json
   ```

2. Verify CORS configuration:
   ```bash
   aws s3api get-bucket-cors --bucket landten-incident-photos
   ```

### Problem: Presigned URL expired

**Symptoms:**
```
The provided token has expired
```

**Solutions:**
1. Generate new presigned URL (backend handles this automatically)
2. Check URL expiration time (default: 3600 seconds)
3. Ensure system clocks are synchronized

### Problem: File upload too large

**Symptoms:**
```
413 Request Entity Too Large
```

**Solutions:**
1. Check file size limit in backend:
   ```python
   # In route handler
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
   ```

2. Add file size validation on frontend before upload

3. For larger files, implement multipart upload

---

## Payment Issues

### Problem: Stripe PaymentIntent creation fails

**Symptoms:**
```
stripe.error.AuthenticationError: Invalid API Key provided
```

**Solutions:**
1. Verify Stripe secret key in `backend/.env`:
   ```bash
   STRIPE_SECRET_KEY=sk_test_51...
   ```

2. Check key in Stripe Dashboard:
   https://dashboard.stripe.com/test/apikeys

3. Ensure using test key for development (starts with `sk_test_`)

### Problem: Payment succeeds but job not marked as paid

**Symptoms:**
Payment goes through in Stripe but job status doesn't update

**Solutions:**
1. Check webhook configuration:
   ```bash
   echo $STRIPE_WEBHOOK_SECRET
   ```

2. Verify webhook endpoint in Stripe Dashboard:
   https://dashboard.stripe.com/test/webhooks

3. Check webhook logs in Stripe Dashboard

4. Test webhook locally with Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/payments/webhooks/stripe
   ```

### Problem: Platform fee not applied correctly

**Symptoms:**
Contractor receives full payment instead of 85%

**Solutions:**
1. Check platform fee configuration in `.env`:
   ```bash
   STRIPE_PLATFORM_FEE_PERCENT=15
   ```

2. Verify payment calculation in backend:
   ```python
   contractor_amount = total_amount * 0.85
   platform_fee = total_amount * 0.15
   ```

3. Check Stripe transfer breakdown in dashboard

---

## Webhook Issues

### Problem: Webhook signature verification fails

**Symptoms:**
```
stripe.error.SignatureVerificationError: No signatures found matching the expected signature
```

**Solutions:**
1. Check webhook secret in `.env`:
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

2. Get correct secret from Stripe Dashboard → Webhooks → Endpoint

3. For local testing, use Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/payments/webhooks/stripe
   # Copy the webhook secret (whsec_...) to .env
   ```

### Problem: Duplicate webhook events

**Symptoms:**
Same payment processed multiple times

**Solutions:**
1. Verify idempotency key implementation:
   ```python
   # Check if event already processed
   existing = get_payment_by_stripe_event_id(event_id)
   if existing:
       return  # Already processed
   ```

2. Check DynamoDB for duplicate records

3. Stripe automatically retries failed webhooks - ensure idempotency

### Problem: Webhook endpoint not receiving events

**Symptoms:**
Payments succeed but webhook never fires

**Solutions:**
1. Verify webhook endpoint URL in Stripe Dashboard

2. Check endpoint is publicly accessible (use ngrok for local testing):
   ```bash
   ngrok http 8000
   # Use ngrok URL in Stripe Dashboard
   ```

3. Check webhook event types are configured:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`

4. Test with Stripe CLI:
   ```bash
   stripe trigger payment_intent.succeeded
   ```

---

## Docker Issues

### Problem: Docker build fails

**Symptoms:**
```
ERROR [internal] load metadata for docker.io/library/python:3.11-slim
```

**Solutions:**
1. Check Docker daemon is running:
   ```bash
   docker ps
   ```

2. Pull base image manually:
   ```bash
   docker pull python:3.11-slim
   ```

3. Clear Docker cache:
   ```bash
   docker system prune -a
   ```

### Problem: Container exits immediately

**Symptoms:**
```
docker-compose up
# Container starts then exits
```

**Solutions:**
1. Check container logs:
   ```bash
   docker-compose logs backend
   docker-compose logs frontend
   ```

2. Verify environment variables in `docker-compose.yml`

3. Check for errors in application startup

### Problem: Services can't communicate

**Symptoms:**
Frontend can't reach backend in Docker

**Solutions:**
1. Use service names, not localhost:
   ```yaml
   # In docker-compose.yml
   NEXT_PUBLIC_BACKEND_URL=http://backend:8080
   ```

2. Verify services on same network:
   ```bash
   docker network inspect landten_landten-network
   ```

3. Check port mappings in `docker-compose.yml`

---

## Deployment Issues

### Problem: Environment variables not loading

**Symptoms:**
Application crashes in production with missing env vars

**Solutions:**
1. Verify secrets in deployment platform (Heroku, AWS, etc.)

2. Check environment file loaded:
   ```bash
   # For Heroku
   heroku config

   # For AWS
   aws ssm get-parameters --names /landten/prod/*
   ```

3. Ensure `.env` files not committed to git:
   ```bash
   cat .gitignore | grep .env
   ```

### Problem: Database migration fails in production

**Symptoms:**
```
Table already exists
```

**Solutions:**
1. Use idempotent table creation (already implemented in `create_dynamodb_tables.py`)

2. Check existing tables:
   ```bash
   aws dynamodb list-tables
   ```

3. Use different table prefix per environment:
   ```bash
   TABLE_PREFIX=landten_prod python3 scripts/create_dynamodb_tables.py
   ```

### Problem: GitHub Actions deployment fails

**Symptoms:**
CI/CD pipeline fails on deployment step

**Solutions:**
1. Check GitHub Secrets are set:
   - `HEROKU_API_KEY`
   - `HEROKU_APP_NAME`
   - `HEROKU_EMAIL`
   - `STRIPE_SECRET_KEY`
   - `AWS_ACCESS_KEY_ID`
   - etc.

2. Check workflow logs in GitHub Actions tab

3. Verify deployment target is accessible

4. Test deployment manually first

---

## Common Error Messages

### `403 Forbidden` from AWS

**Cause:** Invalid AWS credentials or insufficient permissions

**Fix:**
1. Verify AWS credentials
2. Check IAM policy has DynamoDB and S3 permissions
3. Ensure resource names match (table names, bucket names)

### `500 Internal Server Error`

**Cause:** Unhandled exception in backend

**Fix:**
1. Check backend logs:
   ```bash
   # Docker
   docker-compose logs backend

   # Local
   tail -f backend/logs/app.log
   ```

2. Check Python traceback for specific error

3. Enable debug mode temporarily:
   ```bash
   DEBUG_MODE=true
   LOG_LEVEL=DEBUG
   ```

### `502 Bad Gateway`

**Cause:** Backend not responding or crashed

**Fix:**
1. Check backend is running
2. Check backend health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```
3. Restart backend service

---

## Getting Help

If you encounter an issue not covered here:

1. **Check logs:**
   - Backend: `docker-compose logs backend` or `uvicorn` output
   - Frontend: Browser console and `npm run dev` output
   - Database: CloudWatch logs (AWS) or LocalStack logs

2. **Search existing issues:**
   - GitHub Issues
   - Stripe Documentation
   - AWS Documentation

3. **Create a detailed bug report:**
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Error messages and logs
   - Environment details (OS, Python version, Node version)

4. **Test in isolation:**
   - Does it work locally but not in production?
   - Does it work with test data?
   - Can you reproduce with minimal example?

---

## Preventive Maintenance

### Regular checks:

1. **Monitor error rates:**
   - Set up CloudWatch alarms
   - Monitor Stripe webhook delivery success rate
   - Track API response times

2. **Review logs weekly:**
   - Look for warning patterns
   - Check for failed payments
   - Identify slow queries

3. **Keep dependencies updated:**
   ```bash
   # Backend
   pip list --outdated

   # Frontend
   npm outdated
   ```

4. **Run health checks:**
   ```bash
   ./scripts/test_flow.sh
   ```

5. **Backup DynamoDB tables regularly:**
   ```bash
   aws dynamodb create-backup --table-name landten_prod_incidents --backup-name incidents_backup_$(date +%Y%m%d)
   ```

---

**Last Updated:** December 2024
**Version:** 3.0
