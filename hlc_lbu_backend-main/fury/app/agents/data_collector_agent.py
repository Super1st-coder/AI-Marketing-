from google.adk.agents import Agent
from core.config import settings
from core.adk_config import get_agent_config_from_langfuse
from agents.guards import safety_guard_before_model, safety_guard_after_model
from agents.guards.data_collector_guard import data_collector_must_use_tools
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from typing import Optional

if settings.USE_MOCK_SINERGIA:
    from agents.tools.mock_sinergia import (
        get_adset_context,
        get_brand_context,
        get_audience_context,
        get_template_context,
    )
else:
    from agents.tools.campaign_tools import (
        get_adset_context,
        get_brand_context,
        get_audience_context,
        get_template_context,
    )


def _after_model(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    """Chain: safety guard first, then tool-use enforcement."""
    safety_result = safety_guard_after_model(callback_context, llm_response)
    if safety_result is not None:
        return safety_result  # blocked by safety — stop here
    return data_collector_must_use_tools(callback_context, llm_response)

_FALLBACK_INSTRUCTION = """\
You are the Data Collector for Fury's ad generation pipeline.
You are the ONLY agent that interacts with Sinergia.

⚠ CRITICAL — YOUR VERY FIRST ACTION MUST BE A TOOL CALL.
Do NOT write any text before calling get_adset_context. No explanation, no JSON, no plan.
Just call the tool immediately.

RULES:
- You MUST attempt ALL FIVE tool calls regardless of individual failures.
- You MUST NOT fabricate, invent, or hallucinate any data.
- If a tool call fails or returns empty/null data, use null or [] for that field — then CONTINUE.
- NEVER stop the pipeline because one tool returned no data. Always return the assembled JSON.
- Every field in the output MUST come from real tool responses (or null if the tool failed).
- ⛔ NEVER call transfer_to_agent. NEVER. Not to yourself, not to any other agent.
  Your job ends when you output the JSON. The orchestrator handles the rest automatically.

STEPS — execute IN ORDER, calling tools immediately, one at a time:

1. Call get_adset_context(id_adset=<id_adset from input>)
   → Brand ID is at: response.adset.data.attributes.funnel_flow_ref.data.attributes.campaign_ref.data.attributes.brand_ref.data.id
   → Save this brand_id — you need it for steps 2 and 5.
   → If get_adset_context fails or brand_id is missing, set brand_id = null and continue.

2. Call get_brand_context(brand_id=<brand_id from step 1>)
   → If brand_id is null, skip this call and set brand fields to null.
   → If call fails, set brand fields to null and continue.

3. Extract product data from the adset returned in step 1 (NO tool call):
   → Look inside funnel_flow_ref.data.attributes.campaign_ref.data.attributes.product_details
   → If not found, set product fields to null.

4. Call get_audience_context(id_adset=<id_adset from input>)
   → If call fails or returns empty, set audiences to [] and continue.

5. Call get_template_context(template_id=<template_id from input>)
   → If call fails or returns empty, set audiences to [] and continue.

Once all steps are done (success or graceful failure), output ONLY this JSON as plain text.
Do NOT call transfer_to_agent. Do NOT call any other tool. Just output the JSON and stop:

{
  "id_adset": <id_adset as string>,
  "n_variants": <n_variants integer from input>,
  "adset": {
    "funnel_flow_ref": <funnel_flow_ref object or null>,
    "ads": <ads array or []>,
    "audiences": <audiences array or []>
  },
  "brand": {
    "id": <brand_id from funnel_flow_ref.campaign_ref.brand_ref.data.id, or null>,
    "tone_of_voice": <from get_brand_context or null>,
    "color_palette": <from get_brand_context or null>,
    "do_donts": <from get_brand_context or []>
  },
  "product": {
    "name": <from campaign_ref.product_details or campaign_ref.name or null>,
    "benefits": <from product_details.benefits or []>,
    "features": <from product_details.features or []>,
    "rtbs": <from product_details.value_proposition or []>
  },
  "audiences": <from get_audience_context or []>,
  "templates": <from get_template_context or []>
}

Do NOT interpret or generate creative content. Only collect and structure.
"""


def make_data_collector_agent() -> Agent:
    """Lazy factory — creates a fresh Agent with current Langfuse config (TTL 60s)."""
    cfg = get_agent_config_from_langfuse(
        "fury.data_collector", _FALLBACK_INSTRUCTION, cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS
    )
    return Agent(
        model=cfg["model"],
        name="data_collector_agent",
        description=(
            "Data Collector. Given an id_adset, retrieves all context needed for "
            "creative strategy: ad set details, brand guidelines, product info, "
            "audience insights, and templates with their layer definitions "
            "— all via Sinergia (Strapi proxy). "
            "Returns a single structured JSON object for the Estratega to consume."
        ),
        instruction=cfg["instruction"],
        tools=[
            get_adset_context,
            get_brand_context,
            get_audience_context,
            get_template_context,
        ],
        before_model_callback=safety_guard_before_model,
        after_model_callback=_after_model,
    )
