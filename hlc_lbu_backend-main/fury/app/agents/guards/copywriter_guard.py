from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types as genai_types

from core.logging import get_logger

logger = get_logger(__name__)

_CW_TOOLS_CALLED_KEY = "cw_called_tools"
_CW_TOOLS_STARTED_KEY = "cw_tools_started"
_REQUIRED_TOOLS = {"get_ctas"}


def _extract_channel_name(callback_context: CallbackContext, llm_response: LlmResponse) -> str:
    state = callback_context.state
    # If any explicit channel_name exists in session state, use it.
    channel_name = state.get("channel_name") or state.get("channel_id")

    # Try to extract from adset data if available
    if not channel_name:
        adset = state.get("adset")
        if adset and isinstance(adset, dict):
            # Assuming adset has channel info, e.g., adset.get("channel_name")
            channel_name = adset.get("channel_name") or adset.get("channel_id")

    # Fallback to parsing from response text
    if not channel_name and llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.text:
                import re
                m = re.search(r"channel_(?:name|id)\s*[=:]\s*['\"]?([\w\- ]+)['\"]?", part.text)
                if m:
                    channel_name = m.group(1).strip()
                    break

    # Default if nothing found
    return channel_name or "default"


def copywriter_must_use_tools(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Enforce that copywriter calls get_ctas at least once before generating final output."""
    state = callback_context.state

    # Track which tools have been called.
    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.function_call is not None:
                tool_name = part.function_call.name
                called_set: set = state.get(_CW_TOOLS_CALLED_KEY, set())
                called_set.add(tool_name)
                state[_CW_TOOLS_CALLED_KEY] = called_set

                if tool_name in _REQUIRED_TOOLS:
                    state[_CW_TOOLS_STARTED_KEY] = True

                break

    has_function_call = any(
        part.function_call is not None
        for part in (llm_response.content.parts or [])
        if llm_response.content
    )

    if has_function_call:
        return None  # Allow tool calls to proceed

    # Check if any required CTA tool has been called at least once
    called_tools = state.get(_CW_TOOLS_CALLED_KEY, set())
    if called_tools.intersection(_REQUIRED_TOOLS):
        return None  # Allow the response since a CTA tool was called

    preferred_tool = "get_ctas"

    # If any required CTA tool has not been called and this is a text response (likely final JSON), force the call
    channel_name = _extract_channel_name(callback_context, llm_response)
    logger.warning(
        f"[CopywriterGuard] forzando llamada a {preferred_tool}, "
        "porque no se ha llamado antes de generar la respuesta final."
    )

    forced = LlmResponse(
        content=genai_types.Content(
            role="model",
            parts=[
                genai_types.Part(
                    function_call=genai_types.FunctionCall(
                        name=preferred_tool,
                        args={},
                    )
                )
            ],
        )
    )
    return forced