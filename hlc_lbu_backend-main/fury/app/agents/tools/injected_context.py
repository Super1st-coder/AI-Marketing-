"""The Adset_Context is injected by the pipeline, never fetched by the agents.

`job_runner_service._run_phase1` calls `get_adset_context` ONCE, strips the signed URLs
and appends it to every agent input under the "FULL ADSET CONTEXT" header. The
Estratega, Copywriter and Image_Prompter therefore no longer get the real tool.

`get_adset_context` below is a stub with the same name: older Langfuse prompts still
tell the model to call it, and ADK fails the whole run (ValueError "not found in the
tools_dict") when a model calls an unregistered tool. The stub makes no network call
and points the model back to the injected block, costing at most one extra turn.
"""
from __future__ import annotations

from core.logging import get_logger

logger = get_logger(__name__)

INJECTED_CONTEXT_HEADER = "FULL ADSET CONTEXT"

# Appended to the Langfuse prompts (scripts/langfuse_update_prompt_contract.py) and to
# the fallbacks. Never use double braces here: Langfuse compiles prompts with mustache.
CONTEXT_SOURCE_MARKER = "CONTEXT SOURCE — INJECTED ADSET CONTEXT"
CONTEXT_SOURCE_SECTION = f"""
════════════════════════════════════════════════
{CONTEXT_SOURCE_MARKER}
════════════════════════════════════════════════
This overrides ANY earlier instruction to call get_adset_context (including "your very
first action must be a tool call to get_adset_context").

- The complete Ad Set context (brand, product, campaign, buyer, audience,
  creative_angle) is ALREADY in your input, after the line that starts with
  "{INJECTED_CONTEXT_HEADER}". It is the only source of that data.
- Do NOT call get_adset_context. Read every product, campaign, brand, buyer and
  audience field you need (e.g. product.id) from that block instead.
- Your other tools are still available and still required where your instructions
  ask for them.
- If a field is missing from the injected block, use null or [] and continue.
"""


def get_adset_context(id_adset: int) -> dict:
    """Do not call: the full Ad Set context is already in your input, under the line
    that starts with "FULL ADSET CONTEXT". Read it from there.

    Args:
        id_adset: ignored.
    """
    logger.warning(
        f"agent called get_adset_context(id_adset={id_adset}) although the context is "
        f"injected; returning a notice (no Sinergia call)"
    )
    return {
        "ok": False,
        "error": "context_already_provided",
        "message": (
            'Do not call get_adset_context. The full Ad Set context is already in your '
            'input, after the line that starts with "FULL ADSET CONTEXT". Read it from '
            'there and continue with your other tools.'
        ),
    }
