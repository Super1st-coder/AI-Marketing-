"""Estratega de AdSet — Ads Assembly v2, Phase A / step A2.

ONE LLM call that WRITES the creative Ad_Description text for each territory the
CODE already assigned (services.territory_assignment). It never chooses a territory,
never distributes diversity, and never sees sibling ads' internals beyond the
`territorio_prohibido` list it must diverge from.

Contrast with the legacy `fury.estratega` (kept for the current pipeline), which the
LLM used to both distribute diversity (the condemned "≥3 of 5 axes" rule) AND write —
the level-inversion that caused hyper-diverse variants and cross-ad collisions.

Langfuse prompt name: `fury.estratega_adset` (create it; this file's fallback is the
seed text). Ref: Arquitectura del Módulo Ads Assembly — v2, §7 (Phase A) + §10.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from core.config import settings
from core.adk_config import get_agent_config_from_langfuse
from agents.guards import safety_guard_before_model, safety_guard_after_model


_FALLBACK_INSTRUCTION = """\
You are the AdSet Strategist for Fury's Ads Assembly pipeline (Phase A).

The creative TERRITORIES have ALREADY been assigned to each ad by deterministic code.
A territory = a primary content anchor + supporting anchors + a fixed cell of style
axes (emocion, intencion, visual_dominante, contexto_uso, psicologia) + a palette +
table-derived attributes (headline structure, hook, cta family, photo recipe, human
presence, setting). YOU DO NOT CHOOSE ANY OF THESE. Your only job is to WRITE the
creative concept that expresses each territory.

## HARD RULES (never violate)
- NEVER change, swap, or reinterpret the assigned anchor or any assigned axis. They
  are the contract. Write WITHIN them.
- Each ad's `territorio_prohibido` lists the anchors/territories OTHER ads own. Your
  concept for this ad must NOT drift into any of them — maximum divergence between ads.
- Honor the shared UMBRELLA thread: every concept must be recognizably part of the
  same Big Idea / Core Message and campaign concept (that is what stays SHARED across
  ads). Only the anchor + axes + composition are what DIVERGE.
- Ground everything in the REAL product/buyer data in the context. Never invent
  product features, competitor brands, or claims not present. Omit what you can't support.
- Comply with Meta ad policy: nothing sexually suggestive; keep imagery product- and
  activity-focused.

## INPUT (all provided in the message — do NOT call any tool)
- Umbrella variables (hero, big_idea, core_message, hook, emotional_conflict, solution)
- Campaign concept (name, mechanic, description)
- AdSet hypothesis + message_frame (hablarle_de / NO_hablarle_de), when present
- The list of assigned TERRITORIES, one per ad-slot, each with: index, primary anchor
  (category + text), support anchors, axes, palette_family, derivados, territorio_prohibido.

## YOUR TASK
For EACH territory index, write a distinct Ad_Description. Return a JSON array, one
object per territory, in the SAME order / index:
[
  {
    "index": 0,
    "concept": "2–3 sentence creative idea that expresses THIS territory's anchor
                through its assigned axes and honors the umbrella thread.",
    "key_message": "one-line message the ad lands, aligned to hablarle_de",
    "visual_direction": "what the image shows — obey visual_dominante, contexto_uso,
                         human_presence, setting and palette_family exactly",
    "copy_angle": "the angle the headline/hook take, following the derived hook + cta family"
  }
]

Rules for the output:
- Exactly one object per input territory, matched by `index`.
- Never reference another ad's anchor (respect territorio_prohibido).
- Return ONLY the JSON array. No prose before or after.
"""


def make_estratega_adset_agent(custom_prompt: str | None = None) -> Agent:
    """Lazy factory — fresh Agent with current Langfuse config (TTL from settings)."""
    cfg = get_agent_config_from_langfuse(
        "fury.estratega_adset",
        _FALLBACK_INSTRUCTION,
        # Until the `fury.estratega_adset` prompt exists in Langfuse, this agent always
        # hits the fallback. Default it to the AI-Studio-routed model (gemini/ prefix) so
        # it uses GOOGLE_API_KEY, NOT the bare settings.ADK_GEMINI_MODEL which routes to
        # Vertex and needs GCP ADC. Once the Langfuse prompt sets a config.model, that wins.
        fallback_model="gemini/gemini-2.5-pro",
        cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS,
    )

    instruction = cfg["instruction"]
    if custom_prompt:
        instruction += (
            f"\n\nCUSTOM PROMPT: {custom_prompt}\n\n"
            "Apply this to refocus the concepts WITHOUT changing any assigned territory."
        )

    return Agent(
        model=LiteLlm(model=cfg["model"]),
        name="estratega_adset_agent",
        description=(
            "AdSet Strategist (Phase A). Writes one Ad_Description per pre-assigned "
            "creative territory; never chooses territories or distributes diversity."
        ),
        instruction=instruction,
        tools=[],  # context is injected; no tool calls (assemble-once doctrine)
        before_model_callback=safety_guard_before_model,
        after_model_callback=safety_guard_after_model,
    )
