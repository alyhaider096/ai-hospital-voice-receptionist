from fastapi import APIRouter

from app.api.routes import admin, auth, health, vapi

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(vapi.router)
api_router.include_router(admin.router)
