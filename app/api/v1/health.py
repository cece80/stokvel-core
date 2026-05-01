from fastapi import APIRouter, HTTPException
from app.core.redis import get_redis

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    redis = await get_redis()
    try:
        pong = await redis.ping()
        if pong:
            return {"status": "ok"}
        else:
            raise HTTPException(status_code=500, detail="Redis unavailable")
    except Exception:
        raise HTTPException(status_code=500, detail="Redis unavailable")
