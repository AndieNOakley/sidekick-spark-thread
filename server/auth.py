# server/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

# in-memory registry of valid tokens
ISSUED_TOKENS: set[str] = set()

def add_token(token: str) -> None:
    ISSUED_TOKENS.add(token)

def require_token(creds: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = creds.credentials
    if token not in ISSUED_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
