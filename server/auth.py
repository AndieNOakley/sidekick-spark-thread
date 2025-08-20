# server/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def require_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Simple token-based authentication.
    Replace 'mysecrettoken' with your actual token (or load from env).
    """
    token = credentials.credentials
    if token != "mysecrettoken":  # <-- change this
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
