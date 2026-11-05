"""Health check endpoints"""
from fastapi import APIRouter
from schemas.common import HealthResponse
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint (Deep Check)
    """
    import psycopg
    from qdrant_client import QdrantClient
    from fastapi import HTTPException
    import httpx
    
    services_status = {
        "strapi": "checking...",
        "qdrant": "checking...",
        "postgres": "checking...",
        "openai": "checking...",
        "gemini": "checking..."
    }
    
    try:
        # Check Postgres
        conn_str = settings.POSTGRES_CONNECTION_STRING.replace("postgresql+psycopg://", "postgresql://")
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        services_status["postgres"] = "ok"
        
        # Check Qdrant
        qdrant = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        collections = qdrant.get_collections()
        services_status["qdrant"] = "ok"
        
        # Check Strapi
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Check if Strapi server is alive
            strapi_response = await client.get(f"{settings.STRAPI_URL}/_health")
            strapi_response.raise_for_status()
            
            # Check if API Token is valid
            headers = {"Authorization": f"Bearer {settings.STRAPI_TOKEN}"}
            token_response = await client.get(f"{settings.STRAPI_URL}/api/accounts?pagination[limit]=1", headers=headers)
            if token_response.status_code in (401, 403):
                raise Exception(f"Strapi token is invalid or missing permissions: HTTP {token_response.status_code}")
                
        services_status["strapi"] = "ok"

        # Check OpenAI
        openai_key = settings.OPENAI_API_KEY
        if not openai_key or "your_openai_key_here" in openai_key or openai_key == "dummy":
            services_status["openai"] = "dummy_key"
        else:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    openai_headers = {"Authorization": f"Bearer {openai_key}"}
                    openai_resp = await client.get("https://api.openai.com/v1/models", headers=openai_headers)
                    if openai_resp.status_code == 200:
                        services_status["openai"] = "ok"
                    elif openai_resp.status_code == 401:
                        services_status["openai"] = "invalid_key"
                    else:
                        services_status["openai"] = f"error: HTTP {openai_resp.status_code}"
            except Exception as e:
                services_status["openai"] = f"error: {str(e)}"

        # Check Gemini / Google AI Studio
        gemini_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY
        if not gemini_key or "your_gemini_key_here" in gemini_key or gemini_key == "dummy":
            services_status["gemini"] = "dummy_key"
        else:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    gemini_resp = await client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}")
                    if gemini_resp.status_code == 200:
                        services_status["gemini"] = "ok"
                    elif gemini_resp.status_code in (400, 403):
                        services_status["gemini"] = "invalid_key"
                    else:
                        services_status["gemini"] = f"error: HTTP {gemini_resp.status_code}"
            except Exception as e:
                services_status["gemini"] = f"error: {str(e)}"
        
        return HealthResponse(
            status="healthy",
            version=settings.APP_VERSION,
            services=services_status
        )
    except Exception as e:
        import re
        error_msg = str(e)
        error_msg = re.sub(r'(://[^:]+:)[^@]+(@)', r'\1***\2', error_msg)
        logger.error(f"Health check failed: {error_msg}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {error_msg}")


@router.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "health": "/health",
            "generate_text": "/ad/media/elements/generate_text",
            "docs": "/docs"
        }
    }

