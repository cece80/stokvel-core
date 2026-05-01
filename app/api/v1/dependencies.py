from fastapi import Depends, HTTPException, Header, status
from app.core.security import verify_jwt_token
from app.models.user import UserContext

async def get_current_user(authorization: str = Header(...)) -> UserContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        user_ctx = verify_jwt_token(token)
        return user_ctx
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
