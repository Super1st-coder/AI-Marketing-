"""Validador Agent — checks creative diversity on copy + image prompts BEFORE image generation."""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.adk_config import get_agent_config_from_langfuse
from agents.tools.validation_tools import check_diversity_and_fidelity
from agents.guards import safety_guard_before_model, safety_guard_after_model

_FALLBACK_INSTRUCTION = """\
You are the Andromeda Quality Validator for Fury.

⚠️ CRITICAL — YOUR VERY FIRST ACTION MUST BE A TOOL CALL.
Do NOT write any text before calling check_diversity_and_fidelity. No explanation, no JSON, no plan.
Just call the tool immediately with the proposals list.

You receive the complete proposals list — each proposal contains:
  - plan: { id, emocion, intencion, visual_dominante, contexto_uso, psicologia, template_id }
  - copy: { headline, cta, description, primary_text }
  - image_prompts: list

Use check_diversity_and_fidelity(proposals) to evaluate all pairs.

The function checks 4 dimensions:
  1. Strategic axes (S_axes × 0.50) — hard fail if >2 axes identical
  2. Copy texts (S_text × 0.25) — Jaccard on headline+cta+primary_text+description
  3. Image prompts (S_image_prompt × 0.15) — lexical similarity of prompts
  4. Template overlap (S_template × 0.10) — penalty for same template_id

S_final(i,j) = 0.50*S_axes + 0.25*S_text + 0.15*S_image_prompt + 0.10*S_template
Hard fail: count_same_axes > 2
Soft fail: S_final >= 0.55

The tool returns a JSON with this EXACT structure:
{
  "ok": true,
  "overall_pass": true | false,
  "conflicts": [
    {
      "plan_i": "plan_1",
      "plan_j": "plan_2",
      "same_axes": 3,
      "s_axes": 0.6,
      "s_text": 0.45,
      "s_template": 1.0,
      "s_final": 0.625,
      "hard_fail": true,
      "soft_fail": true
    }
  ],
  "subset_to_regenerate": ["plan_1", "plan_2"],
  "threshold_used": 0.55
}

⚠️ CRITICAL: Return the tool's JSON output EXACTLY as received.
DO NOT modify, summarize, or add commentary.
DO NOT wrap it in markdown code blocks.
Just return the raw JSON object.

The orchestrator will:
- If overall_pass=true: proceed to NanoBanana for image generation
- If overall_pass=false: send subset_to_regenerate back to Estratega for retry
"""


def make_validador_agent() -> Agent:
    """Lazy factory — creates a fresh Agent with current Langfuse config (TTL 60s)."""
    cfg = get_agent_config_from_langfuse(
        "fury.validador", _FALLBACK_INSTRUCTION, cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS
    )

    model=LiteLlm(model=cfg["model"])

    return Agent(
        model=model,
        name="validador_agent",
        description=(
            "Validador Andromeda. Evaluates creative proposals (copy + image_prompts) "
            "for diversity BEFORE image generation. Checks 4 dimensions: strategic axes, "
            "copy similarity, image prompts similarity, and template overlap. "
            "Returns overall_pass and subset_to_regenerate for the retry loop."
        ),
        instruction=cfg["instruction"],
        tools=[check_diversity_and_fidelity],
    )
