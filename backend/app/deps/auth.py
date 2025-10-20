import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer(auto_error=False)

def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    # Dev-mode bypass controlled by env AUTH_DISABLED
    if os.getenv("AUTH_DISABLED", "false").lower() in {"1", "true", "yes"}:
        return "dev-mode"

    # TODO: Integrate firebase-admin in production
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return credentials.credentials
