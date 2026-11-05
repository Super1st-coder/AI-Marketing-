"""Application configuration"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from core.logging import get_logger

logger = get_logger(__name__)

class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "Fury API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    API_V2_PREFIX: str = "/api/v2"
    
    # Strapi
    STRAPI_URL: str = "http://strapi:1337"
    STRAPI_TOKEN: Optional[str] = None
    
    # N8N
    N8N_URL: str = "http://n8n:5678"
    
    # Qdrant
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: Optional[str] = None
    
    DATABASE_HOST: Optional[str] = None
    DATABASE_PORT: Optional[int] = None
    DATABASE_USERNAME: Optional[str] = None
    DATABASE_PASSWORD: Optional[str] = None
    DATABASE_NAME_DEFAULT: Optional[str] = None
    
    @property
    def POSTGRES_CONNECTION_STRING(self) -> str:
        """Generate PostgreSQL connection string from environment variables"""
        if not all([self.DATABASE_USERNAME, self.DATABASE_PASSWORD, self.DATABASE_HOST, self.DATABASE_PORT, self.DATABASE_NAME_DEFAULT]):
            raise ValueError("PostgreSQL configuration is incomplete. Please set all required environment variables in .env file")
        return f"postgresql+psycopg://{self.DATABASE_USERNAME}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME_DEFAULT}"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 1.2

    # Sinergia (Strapi proxy)
    SINERGIA_URL: str = "http://sinergia:60000"
    SINERGIA_SERVICE_API_KEY: Optional[str] = None  # shared secret for Fury→Sinergia service auth
    USE_MOCK_SINERGIA: bool = False  # set True locally to skip Sinergia entirely

    # Ads Assembly v2 — Phase-A creative-territory engine (deterministic diversity).
    # When True, STEP 2 assigns territories in code + writes them via estratega_adset,
    # instead of the legacy estratega's per-variant diversity. Off by default.
    USE_TERRITORY_ENGINE: bool = False

    # adset-creative-diversity: one Creative_Plan per Ad, diversity assigned per Adset in
    # code (territory_assignment) and verified by diversity_checker + validador.
    # False keeps the legacy path (incl. USE_TERRITORY_ENGINE) unchanged.
    USE_ADSET_CREATIVE_DIVERSITY: bool = False

    # adset-creative-diversity (P15): image elements of the Ad_Template whose name
    # contains any of these patterns (case-insensitive) are decorative and get no
    # generated image. Env format: JSON list.
    ADSET_DECORATIVE_IMAGE_PATTERNS: list[str] = ["degradado", "gradient", "overlay", "mask", "shape"]

    # HL-2630 — max concurrent NanoBanana image generations per job. Each in-flight
    # generation holds image bytes + (in composite mode) the rembg/onnxruntime model in
    # memory, so unbounded fan-out OOM-killed the Celery worker. Bounds peak memory;
    # lower to 1 if workers are still tight, raise once RAM headroom is confirmed.
    IMAGE_GEN_MAX_CONCURRENCY: int = 2

    # HL-2630 — hard timeout (seconds) for a single NanoBanana image generation. Without it
    # the Gemini call has NO client timeout: a stalled request (observed during Gemini "high
    # demand" spikes) hung the worker 15+ min holding image bytes until it was OOM/SIGKILLed,
    # instead of failing fast so Celery can retry. Applied both at the google-genai HTTP layer
    # (so the socket actually returns) and as an asyncio.wait_for backstop. Also caps the
    # product-image downloads. Keep comfortably above a normal gen (~5-10s) but well under the
    # worker's practical patience.
    IMAGE_GEN_TIMEOUT_SECONDS: int = 120

    # Security — internal service auth
    # Sinergia must pass this key in the X-Internal-API-Key header when calling Fury.
    FURY_INTERNAL_API_KEY: Optional[str] = None

    # Security — Google OIDC for Agent Engine endpoints
    # Set to the public URL of this service (Cloud Run URL / Load Balancer URL).
    # Example: https://sec.hiluca.com
    OIDC_AUDIENCE: Optional[str] = None

    # Security — Abyssale & AI Expansion webhook shared secret
    ABYSSALE_WEBHOOK_SECRET: Optional[str] = None

    # Google ADK / Gemini
    GOOGLE_API_KEY: Optional[str] = None
    ADK_GEMINI_MODEL: str = "gemini-2.5-pro"
    GEMINI_API_KEY: Optional[str] = None  # alias for GOOGLE_API_KEY (some ADK components expect this env var)

    # Redis (Celery broker + result backend)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    # Celery
    CELERY_WORKER_MAX_MEMORY_PER_CHILD: int = 1200000  # 1.2 GB in KB
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 10  # Restart worker after this many tasks to free memory
    CELERY_TASK_SOFT_TIME_LIMIT: int = 2700  # 45 min soft limit for a single task (SoftTimeLimitExceeded raised)
    CELERY_TASK_TIME_LIMIT: int = 3600  # 60 min hard limit for

    # Abyssale
    ABYSSALE_API_KEY: Optional[str] = None
    ABYSSALE_BASE_URL: str = "https://api.abyssale.com"
    ABYSSALE_WEBHOOK_CALLBACK_URL: Optional[str] = None

    # AI Expansion service
    AI_EXPANSION_URL: str = "http://localhost:8001/expand"
    AI_EXPANSION_WEBHOOK_URL: str = "http://localhost:8000/api/v2/webhooks/ai-expansion/result"

    PSD_RESIZE_URL: Optional[str] = None

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not set")
    
    # Langfuse
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = ""
    LANGFUSE_PROMPT_NAME: str = "demo-rag-es"
    LANGFUSE_PROMPT_LABEL: str = "production"
    LANGFUSE_CACHE_TTL_SECONDS: int = 60  # TTL for lazy-factory prompt cache (0 = always fresh)
    
    # CORS
    # In production set to explicit origins, e.g.:
    #   CORS_ORIGINS=["https://app.hiluca.com","https://sec.hiluca.com"]
    CORS_ORIGINS: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create global settings instance
settings = get_settings()

