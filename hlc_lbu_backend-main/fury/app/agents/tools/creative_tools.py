"""Creative tools — parallel copy + image generation using asyncio.gather().

This is the KEY parallel-execution tool. The ADK root orchestrator calls this
single async function, which fans out to:
  • OpenAI (copy for each plan)    ─┐
  • Image API (concept per plan)   ─┴─ asyncio.gather() across all plans
Both run concurrently per-plan and all plans run concurrently with each other.
"""
import asyncio
import json
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal async helpers (not exposed as ADK tools themselves)
# ---------------------------------------------------------------------------

async def _generate_copy_for_plan(plan: dict, language: str, llm: ChatOpenAI) -> dict:
    """Generate ad copywriting for a single creative plan."""
    prompt = f"""You are an expert ad copywriter. Generate ad copy for the following creative plan.
Language: {language}
Plan concept: {plan.get('concept', '')}
Tone: {plan.get('tone', '')}
Emotional angle: {plan.get('emotional_angle', '')}

Generate the following text elements as JSON:
{{
  "headline": "max 55 chars",
  "hook": "max 55 chars",
  "punchline": "max 55 chars",
  "cta": "max 55 chars",
  "description": "max 125 chars"
}}
Return only the JSON object, no extra text."""
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        copy_data = json.loads(raw)
    except Exception:
        copy_data = {"raw": response.content}
    return {"plan_id": plan.get("id", ""), "copy": copy_data}


async def _generate_image_concept_for_plan(plan: dict, llm: ChatOpenAI) -> dict:
    """Generate a detailed image prompt for Nano Banana (image API) per plan."""
    prompt = f"""You are a creative director. Generate a detailed image generation prompt for an ad.
Plan concept: {plan.get('concept', '')}
Colour palette: {plan.get('color_palette', '')}
Tone: {plan.get('tone', '')}

Output a single-paragraph image prompt suitable for DALL-E 3 / Imagen.
Focus on visual composition, lighting, subject, style.
Do NOT include text overlays in the image."""
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    image_prompt = response.content.strip()

    # ── Plug your image generation API here ──────────────────────────────
    # Option A – DALL-E 3 (OpenAI):
    #   from openai import AsyncOpenAI
    #   client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    #   img = await client.images.generate(model="dall-e-3", prompt=image_prompt, n=1)
    #   image_url = img.data[0].url
    #
    # Option B – Google Imagen (Vertex AI):
    #   from google.cloud import aiplatform
    #   ...
    # ─────────────────────────────────────────────────────────────────────
    image_url = None  # Replace with actual API call result

    return {
        "plan_id": plan.get("id", ""),
        "image_prompt": image_prompt,
        "image_url": image_url,
    }


# ---------------------------------------------------------------------------
# ADK Tool — exposed to the root orchestrator
# ---------------------------------------------------------------------------

async def generate_creative_content_parallel(
    plans: list[dict],
    language: str = "Spanish",
) -> dict[str, Any]:
    """Generate copywriting and image concepts for ALL plans in parallel.

    Uses asyncio.gather() to run copy-generation and image-concept-generation
    concurrently across all N plans simultaneously.

    Args:
        plans: List of creative plan dicts from the Estratega agent.
               Each plan must have: id, concept, tone, emotional_angle, color_palette.
        language: Language for copy generation (default: Spanish).

    Returns:
        Dict with creative_content list — one entry per plan containing
        copy variants and an image concept/URL.
    """
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
    )

    # Build one (copy, image) gather task per plan
    per_plan_tasks = [
        asyncio.gather(
            _generate_copy_for_plan(plan, language, llm),
            _generate_image_concept_for_plan(plan, llm),
        )
        for plan in plans
    ]

    # Run all plan tasks concurrently
    all_results = await asyncio.gather(*per_plan_tasks, return_exceptions=True)

    creative_content = []
    for i, result in enumerate(all_results):
        if isinstance(result, Exception):
            logger.error(f"Creative generation failed for plan {i}: {result}")
            creative_content.append({"plan": plans[i], "error": str(result)})
        else:
            copy_result, image_result = result
            creative_content.append({
                "plan": plans[i],
                "copy": copy_result["copy"],
                "image_prompt": image_result["image_prompt"],
                "image_url": image_result["image_url"],
            })

    logger.info(f"Parallel creative generation done: {len(creative_content)} plans")
    return {"ok": True, "creative_content": creative_content}
