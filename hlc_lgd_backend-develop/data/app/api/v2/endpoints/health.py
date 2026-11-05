from fastapi import APIRouter
from core.config import settings

router = APIRouter()

@router.get("")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug_mode": settings.DEBUG
    }
