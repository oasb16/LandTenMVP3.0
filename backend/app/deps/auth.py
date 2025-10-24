import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

firebase_admin_available = False
try:
    import firebase_admin
    from firebase_admin import auth as fb_auth, credentials as fb_credentials
    firebase_admin_available = True
except Exception:
    pass

bearer_scheme = HTTPBearer(auto_error=False)

def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    # Dev-mode bypass controlled by env AUTH_DISABLED
    if os.getenv("AUTH_DISABLED", "false").lower() in {"1", "true", "yes"}:
        return "dev-mode"

    # TODO: Integrate firebase-admin in production
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = credentials.credentials

    # Production path using firebase-admin if available and enabled
    if os.getenv("USE_FIREBASE_ADMIN", "false").lower() in {"1","true","yes"}:
        if not firebase_admin_available:
            raise HTTPException(status_code=500, detail="Firebase admin not available")
        if not firebase_admin._apps:
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("FIREBASE_CREDENTIALS")
            if cred_path and os.path.isfile(cred_path):
                firebase_admin.initialize_app(fb_credentials.Certificate(cred_path))
            else:
                firebase_admin.initialize_app()
        try:
            decoded = fb_auth.verify_id_token(token)
            return decoded.get("uid", "user")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid Firebase token")

    # Fallback accepts any non-empty token
    return token
