"""PersonaDataCollector Agent — gathers buyer persona + optional product context from Sinergia.

This is the ONLY agent in the persona image pipeline that interacts with Sinergia.
It mirrors the pattern of data_collector_agent.py.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.adk_config import get_agent_config_from_langfuse
from agents.guards import safety_guard_before_model, safety_guard_after_model

if settings.USE_MOCK_SINERGIA:
    from agents.tools.mock_sinergia import (
        get_buyer_persona_context,
        get_product_context,
        get_image_from_library,
    )
else:
    from agents.tools.campaign_tools import (
        get_buyer_persona_context,
        get_product_context,
        get_image_from_library,
    )


_FALLBACK_INSTRUCTION = """\
You are the Persona Data Collector for Fury's Persona Image Generation pipeline.
You are the ONLY agent that interacts with Sinergia in this pipeline.

⚠ CRITICAL — YOUR VERY FIRST ACTION MUST BE A TOOL CALL.
Do NOT write any text before calling get_buyer_persona_context. No explanation, no JSON, no plan.
Just call the tool immediately.

RULES:
- You MUST attempt ALL relevant tool calls regardless of individual failures.
- You MUST NOT fabricate, invent, or hallucinate any data.
- If a tool call fails or returns empty/null data, use null or [] for that field — then CONTINUE.
- NEVER stop the pipeline because one tool returned no data. Always return the assembled JSON.
- Every field in the output MUST come from real tool responses (or null if the tool failed).
- ⛔ NEVER call transfer_to_agent. NEVER. Not to yourself, not to any other agent.
  Your job ends when you output the JSON. The orchestrator handles the rest automatically.

STEPS — execute IN ORDER, calling tools immediately, one at a time:

1. Call get_buyer_persona_context(id_buyer_persona=<id_buyer_persona from input>)
   → Extract persona name, story, age_range, gender, hometown, pain_points,
     customer_goal, fears_and_worries, barriers_to_making_a_change, and income_level_brackets.
   → If the call fails, set buyer_persona fields to null and continue.

2. [CONDITIONAL — only if id_product is provided and > 0]
   Call get_product_context(id_product=<id_product from input>)
   → Extract product_id name, description, attributes (benefits, features, RTBs/value propositions).
   → If call fails or id_product is null/0, skip and set product fields to null.

3. [CONDITIONAL — only if a product_id was found in step 2]
   Call get_image_from_library(product_id=<product_id from step 2>)
   → Returns a list of product image URLs.
   → Save ALL urls as product_image_urls array.
   → If call fails or returns empty list, set product_image_urls to [] and continue.

Once all steps are done (success or graceful failure), output ONLY this JSON as plain text.
Do NOT call transfer_to_agent. Do NOT call any other tool. Just output the JSON and stop:

{
  "id_buyer_persona": <id_buyer_persona as integer>,
  "n_variations": <n_variations integer from input>,
  "photography_effect": "<photography_effect from input: natural|flash|studio|dramatic>",
  "buyer_persona": {
    "id": <persona id>,
    "name": "<persona name or null>",
    "story": "<persona story or null>",
    "age_range": <age_range array or []>,
    "gender": "<gender or null>",
    "hometown": <hometown array or []>,
    "pain_points": <pain_points array or []>,
    "customer_goal": <customer_goal array or []>,
    "fears_and_worries": <fears_and_worries array or []>,
    "income_level_brackets": <income_level_brackets array or []>,
    "barriers_to_making_a_change": <barriers array or []>,
    "visual_archetype": "<derived description of how this person looks and dresses, or null>"
  },
  "product": {
    "id": <product_id or null>,
    "name": "<product name or null>",
    "description": "<product description or null>",
    "benefits": <benefits array or []>,
    "features": <features array or []>,
    "rtbs": <value_proposition array or []>,
    "image_urls": <product_image_urls array or []>
  }
}

Do NOT interpret or generate creative content. Only collect and structure.
"""


def make_persona_data_collector_agent() -> Agent:
    """Lazy factory — creates a fresh Agent with current Langfuse config."""
    cfg = get_agent_config_from_langfuse(
        "fury.persona_data_collector",
        _FALLBACK_INSTRUCTION,
        cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS,
    )
    model=LiteLlm(model=cfg["model"])
    return Agent(
        model=model,
        name="persona_data_collector_agent",
        description=(
            "Persona Data Collector. Given an id_buyer_persona and optional id_product, "
            "retrieves buyer persona profile, optional product details, and optional product "
            "image URLs from Sinergia. Returns a single structured JSON for the PersonaPrompter."
        ),
        instruction=cfg["instruction"],
        tools=[
            get_buyer_persona_context,
            get_product_context,
            get_image_from_library,
        ],
        # before_model_callback=safety_guard_before_model,
        # after_model_callback=safety_guard_after_model,
    )
