"""AdVariantImagePrompter — describes one edited ad-variant image.

Used by the ad-variant image-edit pipeline, step ``prompt_analysis``
(services/job_runner_service._run_edit_ad_variant_image_pipeline). No tools:
it receives the image inline plus the context assembled by the pipeline
(assemble-once) and returns ONLY ``{"image_prompt": "<description>"}``,
validated by services.ads_validators.validate_ad_variant_image_prompter_response.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.adk_config import get_agent_config_from_langfuse
from agents.guards import safety_guard_before_model, safety_guard_after_model


_FALLBACK_MODEL = "gemini/gemini-2.5-flash"  # keeps the provider prefix for LiteLLM

_FALLBACK_INSTRUCTION = """\
You are the Image Analyst for Fury's ad-variant image editing pipeline.

You receive ONE edited advertising image, the edit instruction that produced it,
and (if available) the prompt of the original base image.

Describe what is actually visible in the image: subject, product, setting,
composition, lighting, colors and mood, in 2-5 sentences, in English.

⚠ CRITICAL RULES:
- Only describe visible content. Do not invent brands, claims, prices or text.
- Comply with Meta advertising policies (no misleading, discriminatory,
  sensational or personal-attribute language).
- Return ONLY a JSON object, with no markdown fences and no extra text:

{"image_prompt": "<description, max 2000 characters>"}
"""


def make_ad_variant_image_prompter_agent(custom_prompt: str | None = None) -> Agent:
    """Lazy factory — creates a fresh Agent with current Langfuse config."""
    cfg = get_agent_config_from_langfuse(
        "fury.ad_variant_image_prompter",
        _FALLBACK_INSTRUCTION,
        fallback_model=_FALLBACK_MODEL,
        cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS,
    )

    instruction = cfg["instruction"]
    if custom_prompt:
        instruction += (
            f"\n\nCUSTOM DIRECTIVE: {custom_prompt}\n"
            "It may refocus the description but never changes the JSON-only output format."
        )

    model = LiteLlm(model=cfg["model"])

    return Agent(
        model=model,
        name="ad_variant_image_prompter",
        description=(
            'Describes an edited ad image as {"image_prompt": str} '
            "for the Sinergia image library."
        ),
        instruction=instruction,
        tools=[],  # Pure reasoning agent — no tool calls needed
        before_model_callback=safety_guard_before_model,
        after_model_callback=safety_guard_after_model,
    )
