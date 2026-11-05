"""
Fury API - Ad Text Generation Service
Main application entry point
"""
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.logging import setup_logging, get_logger
from core.exceptions import FuryException
from api.v2.router import api_router as v2_router

# Setup logging
setup_logging(level="INFO" if not settings.DEBUG else "DEBUG")
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered ad text generation service",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(FuryException)
async def fury_exception_handler(request, exc: FuryException):
    """Handle custom Fury exceptions"""
    logger.error(f"Fury exception: {exc.message} (code: {exc.code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": 0,
            "message": {
                "code": exc.code,
                "text": exc.message
            },
            "details": exc.details
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "ok": 0,
            "message": {
                "code": "INTERNAL_ERROR",
                "text": "Internal server error"
            }
        }
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"PostgreSQL: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info(f"Shutting down {settings.APP_NAME}")


# Include routers
app.include_router(v2_router, prefix=settings.API_V2_PREFIX)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": f"{settings.API_V2_PREFIX}/health"
        }
    }


# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
