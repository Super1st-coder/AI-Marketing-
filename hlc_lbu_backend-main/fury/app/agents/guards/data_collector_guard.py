"""Data-collector-specific callbacks.

`data_collector_must_use_tools` — after_model callback that:
  1. On turn 1: detects hallucinations (text with no tool call) and injects
     a forced get_adset_context call.
  2. On any turn after tools started: detects a self-transfer (transfer_to_agent
     called with the data_collector_agent itself) and blocks it, forcing the
     model to output the assembled JSON directly instead.

In Google ADK, setting tool_config.function_calling_config.mode = ANY causes
infinite loops in multi-agent setups, so instead we intercept the response
*after* the LLM call and correct the behavior programmatically.
"""
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types as genai_types

from core.logging import get_logger

logger = get_logger(__name__)


_TOOLS_STARTED_KEY = "dc_tools_started"
_TOOLS_COMPLETED_KEY = "dc_tools_completed"
_TOOLS_CALLED = {"get_adset_context", "get_brand_context", "get_audience_context", "get_template_context"}

_REQUIRED_TOOL_COUNT = 4


def data_collector_must_use_tools(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Enforce correct tool usage in the data_collector_agent.

    Behaviors
    ---------
    1. Turn 1 hallucination guard:
       If the very first response has no function_call, the model is about
       to hallucinate. Inject a forced get_adset_context call.

    2. Post-collection self-transfer guard:
       After all 4 tools have been called, if the model calls transfer_to_agent
       (especially back to itself or to the parent prematurely), block it and
       return a corrective message asking the model to output the JSON directly.
    """
    state = callback_context.state

    # ------------------------------------------------------------------
    # Track which tools have been called so far
    # ------------------------------------------------------------------
    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.function_call is not None:
                tool_name = part.function_call.name
                called_set: set = state.get("dc_called_tools", set())
                called_set.add(tool_name)
                state["dc_called_tools"] = called_set

                if tool_name in _TOOLS_CALLED:
                    state[_TOOLS_STARTED_KEY] = True

                # Mark complete when all required data tools have fired
                if _TOOLS_CALLED.issubset(called_set):
                    state[_TOOLS_COMPLETED_KEY] = True

    # ------------------------------------------------------------------
    # Check for function_call vs text-only response
    # ------------------------------------------------------------------
    has_function_call = False
    transfer_to_self = False

    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.function_call is not None:
                has_function_call = True
                if part.function_call.name == "transfer_to_agent":
                    agent_name = part.function_call.args.get("agent_name", "")
                    # Block any transfer that happens after all tools are done.
                    # The agent should output JSON, not transfer anywhere.
                    if state.get(_TOOLS_COMPLETED_KEY):
                        transfer_to_self = True
                        logger.warning(
                            f"[DataCollectorGuard] Blocked transfer_to_agent('{agent_name}') "
                            f"after tools completed. Forcing JSON output."
                        )
                break

    # ------------------------------------------------------------------
    # Guard 2: Post-collection self/premature transfer → force JSON output
    # ------------------------------------------------------------------
    if transfer_to_self:
        corrective = LlmResponse(
            content=genai_types.Content(
                role="model",
                parts=[
                    genai_types.Part(
                        text=(
                            "All four tool calls are complete. "
                            "Output ONLY the assembled JSON object now. "
                            "Do NOT call transfer_to_agent or any other tool. "
                            "Just return the JSON."
                        )
                    )
                ],
            )
        )
        return corrective

    # ------------------------------------------------------------------
    # Guard 1: First-turn hallucination (text with no tool call)
    # ------------------------------------------------------------------
    if has_function_call:
        return None  # model is doing the right thing — pass through

    if state.get(_TOOLS_STARTED_KEY):
        # Tools have started — if the model returns text now without a tool
        # call, it is either building the final JSON or thinking out loud.
        # Don't interfere.
        return None

    # First turn, no tool call → hallucination detected
    id_adset = _extract_id_adset(llm_response, callback_context)

    logger.warning(
        f"[DataCollectorGuard] Model skipped tool calls on first turn "
        f"(id_adset={id_adset}). Injecting get_adset_context call."
    )

    forced_response = LlmResponse(
        content=genai_types.Content(
            role="model",
            parts=[
                genai_types.Part(
                    function_call=genai_types.FunctionCall(
                        name="get_adset_context",
                        args={"id_adset": id_adset},
                    )
                )
            ],
        )
    )
    return forced_response


def _extract_id_adset(
    llm_response: LlmResponse,
    callback_context: CallbackContext,
) -> int:
    """Try to pull id_adset from session state or fall back to 0."""
    state = callback_context.state
    for key in ("id_adset", "adset_id"):
        if key in state:
            try:
                return int(state[key])
            except (ValueError, TypeError):
                pass

    # As a last resort parse from the response text
    if llm_response.content and llm_response.content.parts:
        import re
        for part in llm_response.content.parts:
            if part.text:
                m = re.search(r'"id_adset"\s*:\s*"?(\d+)"?', part.text)
                if m:
                    return int(m.group(1))

    logger.error(
        "[DataCollectorGuard] Could not extract id_adset — defaulting to 0. "
        "Ensure id_adset is passed via session state."
    )
    return 0
