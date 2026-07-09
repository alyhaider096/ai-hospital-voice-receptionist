from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import service_error_handler
from app.api.router import api_router
from app.core.config import settings
from app.services.errors import ServiceError


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Backend for Vapi-powered hospital voice appointment booking.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.add_exception_handler(ServiceError, service_error_handler)
    return app


app = create_app()
