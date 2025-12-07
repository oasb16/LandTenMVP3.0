# Vercel Deployment Guide

This guide explains how to properly deploy the LandTenMVP 3.0 frontend to Vercel.

## Project Structure

This is a monorepo with the following structure:
```
LandTenMVP3.0/
├── frontend/        # Next.js application (deploy this to Vercel)
├── backend/         # FastAPI backend (deploy separately)
└── vercel.json      # Minimal vercel configuration
```

## Deployment Steps

### Option 1: Deploy via Vercel Dashboard (Recommended)

1. **Import Your Repository:**
   - Go to [Vercel Dashboard](https://vercel.com/new)
   - Click "Add New Project"
   - Import your GitHub repository

2. **Configure Project Settings:**
   - **Framework Preset:** Next.js
   - **Root Directory:** `frontend` ⚠️ **IMPORTANT: Set this to "frontend"**
   - **Build Command:** `npm run build` (or leave as default)
   - **Output Directory:** `.next` (or leave as default)
   - **Install Command:** `npm install` (or leave as default)

3. **Add Environment Variables:**
   Click "Environment Variables" and add the following:

   ```env
   # NextAuth Configuration
   NEXTAUTH_URL=https://your-app.vercel.app
   NEXTAUTH_SECRET=your-random-secret-string
   NEXTAUTH_TRUST_HOST=true

   # Google OAuth
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret

   # Backend API URL
   NEXT_PUBLIC_BACKEND_URL=https://your-backend-api.com
   BACKEND_INTERNAL_URL=https://your-backend-api.com

   # Stripe (Optional)
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```

4. **Deploy:**
   - Click "Deploy"
   - Wait for the build to complete
   - Your app will be available at `https://your-app.vercel.app`

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel:**
   ```bash
   vercel login
   ```

3. **Deploy from the frontend directory:**
   ```bash
   cd frontend
   vercel
   ```

4. **Follow the prompts:**
   - Link to existing project or create new one
   - Confirm settings
   - Wait for deployment

## Configuration Files

### Root `vercel.json`
The root `vercel.json` is minimal and doesn't interfere with the deployment:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json"
}
```

### Frontend `vercel.json`
The frontend has its own minimal `vercel.json` that Vercel will use when the root directory is set to `frontend`.

## Fixing 404 Errors

If you're experiencing 404 errors on your deployed app:

### 1. Verify Root Directory Setting
The most common cause of 404 errors is incorrect root directory configuration:

- **In Vercel Dashboard:**
  1. Go to Project Settings
  2. Click "General"
  3. Find "Root Directory"
  4. Set it to `frontend`
  5. Save and redeploy

### 2. Check Build Logs
- Go to your deployment in Vercel Dashboard
- Click on the deployment
- Check the "Build Logs" tab for any errors
- Ensure the build completed successfully

### 3. Verify Environment Variables
- Ensure `NEXTAUTH_URL` points to your Vercel deployment URL
- Set `NEXTAUTH_TRUST_HOST=true` to handle Vercel's proxy
- Verify all required environment variables are set

### 4. Check Next.js Configuration
The `frontend/next.config.js` file should have `output` mode compatible with Vercel:
```javascript
const nextConfig = {
  reactStrictMode: true,
  // ... other settings
};
```

## Common Issues and Solutions

### Issue: "Host validation failed" errors

**Solution:** Set these environment variables in Vercel:
```env
NEXTAUTH_TRUST_HOST=true
NEXTAUTH_URL=https://your-actual-vercel-url.vercel.app
```

### Issue: API routes returning 404

**Cause:** Next.js API routes are in `frontend/src/app/api/` and should work automatically.

**Solution:**
- Verify the files exist in `frontend/src/app/api/`
- Check that you're using the App Router (not Pages Router)
- Ensure environment variables are set correctly

### Issue: Backend API not accessible

**Cause:** The backend needs to be deployed separately.

**Solution:**
1. Deploy the backend to a platform like Railway, Render, or AWS
2. Set `NEXT_PUBLIC_BACKEND_URL` to your backend's URL
3. Configure CORS on your backend to allow requests from your Vercel domain

### Issue: Zustand deprecation warnings

**Cause:** These warnings come from dependencies or browser extensions.

**Solution:**
- These warnings don't affect functionality
- Update to the latest versions of all dependencies:
  ```bash
  cd frontend
  npm update
  ```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXTAUTH_URL` | Your Vercel deployment URL | `https://your-app.vercel.app` |
| `NEXTAUTH_SECRET` | Random secret for NextAuth | `openssl rand -base64 32` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `1234567890-abc...` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Secret | `GOCSPX-...` |
| `NEXT_PUBLIC_BACKEND_URL` | Backend API URL (public) | `https://api.example.com` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXTAUTH_TRUST_HOST` | Trust Vercel proxy headers | `true` |
| `BACKEND_INTERNAL_URL` | Backend URL for server-side | Same as `NEXT_PUBLIC_BACKEND_URL` |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe public key | - |

## Monitoring and Debugging

### Check Deployment Status
```bash
vercel ls
```

### View Deployment Logs
```bash
vercel logs <deployment-url>
```

### Check Environment Variables
```bash
vercel env ls
```

## Redeploying

### Trigger a new deployment:
1. Push to your connected git branch (usually `main` or `master`)
2. Or manually trigger from Vercel Dashboard
3. Or use CLI:
   ```bash
   cd frontend
   vercel --prod
   ```

## Support

If you continue to experience issues:
1. Check Vercel's build logs for errors
2. Verify all environment variables are set
3. Ensure the root directory is set to `frontend`
4. Check that your backend is accessible
5. Review the browser console for specific error messages

## Next Steps

After successful deployment:
1. ✅ Configure custom domain (optional)
2. ✅ Set up preview deployments for branches
3. ✅ Configure backend deployment
4. ✅ Test all features in production
5. ✅ Monitor performance and errors
