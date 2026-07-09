from fastapi import APIRouter

from app.api.routes import admin, health, vapi

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(vapi.router)
api_router.include_router(admin.router)

