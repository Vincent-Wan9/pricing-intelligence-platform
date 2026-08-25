import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.exception_handlers import register_exception_handlers
from app.core.redis import redis_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_application: FastAPI):
    try:
        await redis_client.connect()
    except Exception:
        logger.warning("Redis cache is unavailable; database-backed APIs will continue", exc_info=True)
    yield
    await redis_client.close()


def create_app() -> FastAPI:
    application=FastAPI(title=settings.app_name,version=settings.app_version, lifespan=lifespan)
    cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    if cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_exception_handlers(application)
    application.include_router(api_router)

    @application.get("/health",tags=["health"])
    def health() -> dict[str,str]:
        return {"status":"ok"}

    return application


app=create_app()
