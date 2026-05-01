from fastapi import Header, status, HTTPException, Depends
from app.core.security import verify_access_token
from app.models.user import UserContext

def get_current_user(authorization: str = Header(...)) -> UserContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = verify_access_token(token)
        return UserContext(
            user_id=payload.get("sub"),
            org_id=payload.get("org_id"),
            role=payload.get("role"),
            email=payload.get("email"),
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
