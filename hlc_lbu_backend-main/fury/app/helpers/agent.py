import asyncio

from typing import Any, Callable
from langfuse import observe
from core.logging import get_logger
from core.validation import ValidationResult, AgentValidationError

logger = get_logger(__name__)

# Substrings that identify a provider rate-limit / quota error (429 /
# RESOURCE_EXHAUSTED) across Gemini / OpenAI / Bedrock (via LiteLLM).
_RATE_LIMIT_MARKERS = (
    "429", "resource_exhausted", "rate limit", "rate_limit", "ratelimit",
    "quota exceeded", "too many requests",
)


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _RATE_LIMIT_MARKERS)

def _search_key(data, k):
    if k in data:
        return data[k]
    
    for v in data.values():
        if isinstance(v, dict):
            result = _search_key(v, k)
            if result is not None:
                return result
                
    return None

# ---------------------------------------------------------------------------
# ADK runner helper 
# ---------------------------------------------------------------------------

@observe(name="fury.agent_run")
async def run_agent(
    agent, 
    user_id: str, 
    message_text: str, 
    image_data: str | None = None, 
    image_mime_type: str | None = None,
    validator: Callable[[str], ValidationResult] | None = None,
    initial_state: dict | None = None
) -> str | dict | list:
    """Run an ADK agent and return its final response.

    Args:
        agent: The agent to run
        user_id: User ID for session
        message_text: Text prompt for the agent
        image_data: Optional base64 image data URI to attach to the message
        image_mime_type: Optional MIME type of the image (e.g. "image/png")
        validator: Optional callable that takes the response text and returns ValidationResult
                   If validation fails, raises AgentValidationError
        initial_state: Optional initial state for the session

    Returns:
        The raw response TEXT, or — when the validator supplies
        `ValidationResult.data` — the PARSED dict/list instead. Callers cannot
        tell which they got, so anything that post-processes this must tolerate
        both (see `_parse_json_response` in the job runners).

    Raises:
        AgentValidationError: If the validator is provided and the response fails validation
    """
    from google.genai import types
    from core.adk_config import get_runner, session_service

    runner = get_runner(agent)

    # Build message parts with optional image (static across retries)
    parts = [types.Part(text=message_text)]
    
    if image_data:
        try:
            # Parse base64 data URI: data:image/png;base64,xxxx
            if image_data.startswith('data:image/'):
                header, b64data = image_data.split(',', 1)
                import base64
                img_bytes = base64.b64decode(b64data)
                
                # Extract mime type from header (format: data:image/jpeg;base64)
                # Split by ':' to get 'data', then 'image/jpeg;base64'
                # Then split by ';' to get 'image/jpeg'
                mime_type = header.split(':', 1)[1].split(';', 1)[0] if ':' in header else 'image/png'
                
                # Use provided mime_type if available, otherwise extract from header
                final_mime_type = image_mime_type or mime_type
                
                # Add image as part
                parts.append(types.Part.from_bytes(data=img_bytes, mime_type=final_mime_type))
                logger.info(f"  [ADK] Added image to message ({len(img_bytes)} bytes, {final_mime_type})")
        except Exception as img_err:
            logger.warning(f"  [ADK] Failed to process image data: {img_err}")
    
    msg = types.Content(
        role="user",
        parts=parts,
    )
    # Run the agent, retrying on a provider rate-limit (429 / RESOURCE_EXHAUSTED)
    # with exponential backoff so a single rate-limited call doesn't collapse the
    # whole pipeline. A fresh session is created per attempt. Non-rate-limit errors
    # raise immediately (unchanged behaviour).
    from core.config import settings
    max_attempts = int(getattr(settings, "LLM_MAX_RETRIES", 5))
    base_delay = float(getattr(settings, "LLM_RETRY_BASE_DELAY", 2.0))
    max_delay = float(getattr(settings, "LLM_RETRY_MAX_DELAY", 60.0))

    final_text = ""
    event_count = 0
    for attempt in range(1, max_attempts + 1):
        session = await session_service.create_session(
            app_name="fury",
            user_id=user_id,
            state=initial_state or {},
        )
        final_text = ""
        event_count = 0
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=msg,
            ):
                event_count += 1
                author = getattr(event, "author", "?")
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_text = event.content.parts[0].text
                    logger.info(f"  [ADK] final_response from={author} len={len(final_text)}")
                elif hasattr(event, "content") and event.content:
                    for part in (event.content.parts or []):
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            logger.info(f"  [ADK] 🔧 tool_call agent={author} fn={fc.name} args={str(fc.args)[:200]}")
                        elif hasattr(part, "function_response") and part.function_response:
                            fr = part.function_response
                            logger.info(f"  [ADK] 📦 tool_response fn={fr.name} result={str(fr.response)[:200]}")
                        elif hasattr(part, "text") and part.text:
                            logger.info(f"  [ADK] 💬 text agent={author} snippet={part.text[:150]}")
            break  # success — exit retry loop

        except Exception as e:
            if _is_rate_limit_error(e) and attempt < max_attempts:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                logger.warning(
                    f"  [ADK] Rate limit (429) on {agent.name}, "
                    f"attempt {attempt}/{max_attempts} — backing off {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue
            logger.error(f"  [ADK] Error running agent {agent.name}: {e}")
            # Carry the underlying error through: with errors=[] the real cause
            # was logged and then discarded, leaving callers a generic message
            # with no way to tell a rate limit from a bad payload.
            raise AgentValidationError(
                message="ERROR - Processing in IA LLM Model",
                errors=[f"{type(e).__name__}: {e}"],
                step=agent.name,
                code="ERR_PROCESSING_LLM",
            )

    logger.info(f"  [ADK] done total_events={event_count} agent={agent.name}")
    
    # Validate response if validator is provided
    if validator is not None:
        result = validator(final_text)
        if not result.is_valid:
            raise AgentValidationError(
                message=f"Validation failed for agent {agent.name}",
                errors=result.errors,
                step=agent.name,
                code=getattr(result, "error_code", "VALIDATION_ERROR"),
            )
        # If validator returns transformed data, use it
        if result.data is not None:
            return result.data
    
    return final_text
