from fastapi import FastAPI
from app.api.router import api_router
from app.core.config import settings
from app.exception_handlers import register_exception_handlers


def create_app() -> FastAPI:
    application=FastAPI(title=settings.app_name,version=settings.app_version)
    register_exception_handlers(application)
    application.include_router(api_router)

    @application.get("/health",tags=["health"])
    def health() -> dict[str,str]:
        return {"status":"ok"}

    return application


app=create_app()
