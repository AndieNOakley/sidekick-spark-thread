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
   if token != "96c2cb24a1f6427e9d43bb7df0d70535":
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing token",
        headers={"WWW-Authenticate": "Bearer"},
    )
       
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
