from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.exception_handlers import register_exception_handlers


def create_app() -> FastAPI:
    application=FastAPI(title=settings.app_name,version=settings.app_version)
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
