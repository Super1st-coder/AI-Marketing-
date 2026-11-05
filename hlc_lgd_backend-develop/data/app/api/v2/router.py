"""API v2 Router"""
from fastapi import APIRouter
from .endpoints import health, sample

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(sample.router, prefix="/sample", tags=["sample"])

