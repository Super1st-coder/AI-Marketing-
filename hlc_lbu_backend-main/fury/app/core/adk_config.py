"""Google ADK configuration — shared session service and runner factory."""
import os
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

if settings.GOOGLE_API_KEY:
    # ADK / google-genai picks up GOOGLE_API_KEY from environment automatically
    os.environ.setdefault("GOOGLE_API_KEY", settings.GOOGLE_API_KEY)
    logger.info("Gemini API key configured")
else:
    logger.error("GOOGLE_API_KEY is not set — ADK agents will fail")

# ---------------------------------------------------------------------------
# Session Service — Redis-backed, with InMemory fallback
# ---------------------------------------------------------------------------
# RedisSessionService persists ADK sessions across all Celery workers,
# preventing session loss when a task is re-queued to a different worker.
# InMemorySessionService is used as a fallback (dev without Redis, or on
# connection error) so local development keeps working without changes.

def _build_session_service():
    try:
        from core.redis_session_service import RedisSessionService
        svc = RedisSessionService(redis_url=settings.REDIS_URL)
        svc._redis.ping()
        logger.info(f"[ADK] Using RedisSessionService  url={settings.REDIS_URL}")
        return svc
    except Exception as exc:
        logger.warning(
            f"[ADK] Redis unavailable ({exc}) — falling back to InMemorySessionService. "
            "Sessions will NOT persist across worker restarts."
        )
        return InMemorySessionService()


session_service = _build_session_service()


def get_runner(agent) -> Runner:
    """Create an ADK Runner for *agent* using the shared session service."""
    return Runner(
        agent=agent,
        app_name="fury",
        session_service=session_service,
    )


def get_prompt_from_langfuse(name: str, fallback: str) -> str:
    """
    """
    try:
        from langfuse import Langfuse
        lf = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_BASE_URL,
            flush_at=50,
            flush_interval=10,
        )
        lf.clear_prompt_cache()
        prompt = lf.get_prompt(name, label="latest", cache_ttl_seconds=0)
        compiled = prompt.compile()
        logger.info(f"[Langfuse] Loaded prompt '{name}' (version={prompt.version})")
        return compiled
    except Exception as exc:
        logger.warning(f"[Langfuse] Could not load prompt '{name}': {exc} — using fallback.")
        return fallback


def get_agent_config_from_langfuse(
    prompt_name: str,
    fallback_instruction: str,
    fallback_model: str | None = None,
    cache_ttl_seconds: int = 0,
) -> dict:
    """Load agent instruction + model from Langfuse.

    The model is read from the Langfuse prompt's ``config`` field::

        { "model": "gemini-2.0-flash" }

    If the prompt or config key is missing, falls back to
    ``fallback_model`` → ``settings.ADK_GEMINI_MODEL``.

    Args:
        cache_ttl_seconds: Langfuse local cache TTL.
            - 0  → always fresh (used at singleton/boot time)
            - 60 → at most one Langfuse round-trip per minute
                   (recommended for lazy-factory calls inside Celery tasks)

    Returns:
        { "instruction": str, "model": str }
    """
    model = fallback_model or settings.ADK_GEMINI_MODEL
    instruction = fallback_instruction

    try:
        from langfuse import Langfuse
        lf = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_BASE_URL,
            flush_at=50,
            flush_interval=10,
        )
        if cache_ttl_seconds == 0:
            lf.clear_prompt_cache()
        prompt_obj = lf.get_prompt(
            prompt_name, label="latest", cache_ttl_seconds=cache_ttl_seconds
        )
        instruction = prompt_obj.compile()

        if hasattr(prompt_obj, "config") and isinstance(prompt_obj.config, dict):
            lf_model = prompt_obj.config.get("model")
            if lf_model:
                model = lf_model

        logger.info(
            f"[Langfuse] Loaded agent config '{prompt_name}' "
            f"model={model} version={prompt_obj.version} ttl={cache_ttl_seconds}s"
        )
    except Exception as exc:
        logger.warning(
            f"[Langfuse] Could not load agent config '{prompt_name}': {exc} — using fallbacks."
        )

    return {"instruction": instruction, "model": model}
