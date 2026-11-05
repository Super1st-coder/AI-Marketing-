"""API v2 Router"""
from fastapi import APIRouter
from .endpoints import ad_generation, health, variants, jobs, webhooks, agent_tools, persona_images, llm

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(ad_generation.router, prefix="/ad/media/elements", tags=["ad-generation"])
api_router.include_router(variants.router,       prefix="/variants",         tags=["pipeline"])
api_router.include_router(jobs.router,           prefix="/jobs",             tags=["pipeline"])
api_router.include_router(webhooks.router,       prefix="/webhooks",         tags=["webhooks"])
api_router.include_router(agent_tools.router,    prefix="/agent-tools",      tags=["agent-engine-tools"])
api_router.include_router(persona_images.router, prefix="/persona-images",   tags=["persona-images"])
api_router.include_router(llm.router,            prefix="/llm",              tags=["llm-tools"])

