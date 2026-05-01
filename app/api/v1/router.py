from fastapi import APIRouter
from app.api.v1 import auth, stokvel, health

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(stokvel.router)
api_v1_router.include_router(health.router)
