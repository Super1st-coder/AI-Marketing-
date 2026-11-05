"""Template Mapper Agent — maps creative content into Abyssale payload and submits."""
from google.adk.agents import Agent
from core.config import settings
from core.adk_config import get_agent_config_from_langfuse
from agents.tools.abyssale_tools import build_abyssale_payload, post_to_abyssale_and_wait
from agents.guards import safety_guard_before_model, safety_guard_after_model

_FALLBACK_INSTRUCTION = """\
You are the Template Mapper of Fury.

Your job:
1. Use build_abyssale_payload to map the creative_content into Abyssale layers.
   Use the template_id provided in the job context.
   Default format_ratio is '4:5'.
2. Use post_to_abyssale_and_wait to submit the batch and update the job status.

After calling post_to_abyssale_and_wait, report the batch_id and stop.
The pipeline will resume automatically when Abyssale sends the webhook.

Return a JSON summary:
{
  "status": "WAITING_ABYSSALE",
  "batch_id": "...",
  "elements_submitted": N
}
"""


def make_template_mapper_agent() -> Agent:
    """Lazy factory — creates a fresh Agent with current Langfuse config."""
    cfg = get_agent_config_from_langfuse(
        "fury.template_mapper",
        _FALLBACK_INSTRUCTION,
        cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS,
    )
    return Agent(
        model=cfg["model"],
        name="template_mapper_agent",
        description=(
            "Template Mapper. Takes the combined creative content (copy + images) "
            "and maps it into Abyssale layer payloads, then submits the async batch "
            "request. Terminates the runner phase after submission."
        ),
        instruction=cfg["instruction"],
        tools=[build_abyssale_payload, post_to_abyssale_and_wait],
        before_model_callback=safety_guard_before_model,
        after_model_callback=safety_guard_after_model,
    )
