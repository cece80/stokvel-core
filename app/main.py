import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.api.v1.router import api_v1_router
from app.core.redis import get_redis, close_redis
from app.core.exceptions import (
    AppException, AuthError, ValidationError, NotFoundError, RateLimitError
)

@asynccontextmanager
def lifespan(app: FastAPI):
    await get_redis()
    yield
    await close_redis()

def create_app() -> FastAPI:
    app = FastAPI(title="Stokvel OS API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(AuthError)
    async def auth_exception_handler(request: Request, exc: AuthError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(NotFoundError)
    async def notfound_exception_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RateLimitError)
    async def ratelimit_exception_handler(request: Request, exc: RateLimitError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(api_v1_router)
    return app

app = create_app()
