# LandTen MVP 3.0 - Production Setup Guide

## Quick Start

After running Prompts 1-8, deploy to production with:

```bash
./scripts/deploy_production.sh
```

This script automatically:
1. ✅ Validates environment variables
2. ✅ Creates AWS resources (DynamoDB, S3)
3. ✅ Deploys backend to Heroku
4. ✅ Deploys frontend to Vercel
5. ✅ Configures Stripe webhooks
6. ✅ Runs health checks
7. ✅ Tests production flow

## Environment Variables

### Backend (Heroku)
```bash
heroku config:set AWS_ACCESS_KEY_ID=AKIA...
heroku config:set AWS_SECRET_ACCESS_KEY=...
heroku config:set AWS_REGION=us-east-1
heroku config:set STRIPE_SECRET_KEY=sk_live_...
heroku config:set STRIPE_WEBHOOK_SECRET=whsec_...
```

### Frontend (Vercel)
```bash
vercel env add NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
# Enter: pk_live_...
```

## Manual Steps (If Needed)

### 1. Get AWS Credentials
1. Go to AWS Console → IAM
2. Create new user: `landten-production`
3. Attach policies: AmazonDynamoDBFullAccess, AmazonS3FullAccess
4. Create access key
5. Copy Access Key ID and Secret Access Key

### 2. Get Stripe Keys
1. Go to Stripe Dashboard → Developers → API Keys
2. Copy Live mode keys (starts with sk_live_)
3. Publishable key: pk_live_...
4. Secret key: sk_live_...

### 3. Enable Stripe Connect
1. Stripe Dashboard → Connect → Get Started
2. Copy Connect platform client ID
3. Add to environment: STRIPE_CONNECT_CLIENT_ID

## Verification Checklist

After deployment:
- [ ] Backend health check: https://landtenmvp3-55ce0053f28a.herokuapp.com/health
- [ ] Frontend loads: https://land-ten-mvp-3-0.vercel.app
- [ ] Workflow button navigates correctly
- [ ] Can create test incident
- [ ] Can upload photos to S3
- [ ] Can create test job
- [ ] Can submit test bid
- [ ] Stripe webhook receives events

## Monitoring

### View Logs
```bash
# Backend logs
heroku logs --tail -a landtenmvp3

# Frontend logs
vercel logs

# AWS CloudWatch
aws logs tail /landten/backend/application --follow
```

### Health Checks
```bash
curl https://landtenmvp3-55ce0053f28a.herokuapp.com/health
```

## Troubleshooting

### Issue: DynamoDB tables not found
```bash
python scripts/setup_production.py
```

### Issue: S3 bucket access denied
Check CORS configuration:
```bash
aws s3api get-bucket-cors --bucket landten-incident-photos-prod
```

### Issue: Stripe webhook not receiving events
1. Check webhook URL in Stripe Dashboard
2. Verify webhook secret matches env var
3. Test with Stripe CLI:
```bash
stripe listen --forward-to https://landtenmvp3-55ce0053f28a.herokuapp.com/api/v1/payments/webhooks/stripe
```

## Support

- Documentation: /docs/README.md
- API Docs: https://landtenmvp3-55ce0053f28a.herokuapp.com/api/docs
- Issues: Create GitHub issue
