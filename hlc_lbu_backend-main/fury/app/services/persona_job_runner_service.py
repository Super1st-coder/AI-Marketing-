"""Celery tasks for the Persona Image Generation pipeline.

State is stored entirely in the Celery result backend (Redis).
No DB tables. No asyncpg.

Pipeline steps:
  STEP 1 — PersonaDataCollector  : fetch buyer persona + optional product from Sinergia
  STEP 2 — PersonaPrompter       : generate master prompt + N NanoBanana-compatible sub-prompts
  STEP 3 — PersonaAuditor (GATE) : verify prompts against source data — retry loop (max 3 attempts)
  STEP 4 — Image Generation      : generate images via generate_images_from_prompts (NanoBanana)
  STEP 5 — Upload                : upload images to Sinergia library (best-effort per image)
  STEP 6 — Assemble & Return     : store final result in Celery backend
"""
import asyncio
import json
import traceback
from typing import Any, Callable

from core.config import settings
from core.logging import get_logger
from core.validation import ValidationResult, AgentValidationError
from services.celery_app import celery_app
from helpers.agent import run_agent as _run_agent

from langfuse import observe

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Redis helpers (reused pattern from job_runner_service.py)
# ---------------------------------------------------------------------------

def _redis():
    import redis
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


_CHECKPOINT_TTL = 7200  # 2 hours


def _cp_key(task_id: str, step: str) -> str:
    """Redis key for a persona pipeline step checkpoint."""
    return f"fury:persona:cp:{task_id}:{step}"


def _store(key: str, value: Any, ex: int = 86400 * 7):
    _redis().set(key, json.dumps(value), ex=ex)


def _load(key: str) -> Any:
    raw = _redis().get(key)
    return json.loads(raw) if raw else None


def _parse_json_response(text):
    """Parse JSON from an agent response — handles arrays [...] and objects {...}.

    Accepts an ALREADY-PARSED dict/list and returns it untouched: `run_agent`
    returns `ValidationResult.data` (parsed JSON) whenever a validator supplies
    it, and only the raw string otherwise. Callers cannot know which they got,
    so parsing here must be idempotent — without this guard an already-parsed
    response raised `'dict' object has no attribute 'strip'`.
    """
    import re
    if isinstance(text, (dict, list)):
        return text
    if not text or not text.strip():
        return {}
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Failed to parse JSON directly: {e} — trying to extract from text...")
    for pattern in (r"\[.*\]", r"\{.*\}"):
        match = re.search(pattern, cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception as e:
                logger.error(f"Failed to parse JSON from pattern {pattern}: {e}")
    return {"raw": text}

# ---------------------------------------------------------------------------
# Celery task entry point
# ---------------------------------------------------------------------------

@celery_app.task(
    name="services.persona_job_runner_service.run_persona_pipeline",
    bind=True,
    max_retries=3,
)
def run_persona_pipeline(
    self,
    id_buyer_persona: int,
    n_variations: int = 4,
    photography_effect: str = "natural",
    id_product: int | None = None,
    custom_prompt: str | None = None,
):
    """Run the complete persona image generation pipeline as a Celery task."""
    task_id = self.request.id
    logger.info(
        f"[{task_id}] ▶ PersonaPipeline start — "
        f"persona={id_buyer_persona} n={n_variations} effect={photography_effect}"
    )

    self.update_state(state="PROGRESS", meta={
        "step": "starting",
        "id_buyer_persona": id_buyer_persona,
        "n_variations": n_variations,
        "photography_effect": photography_effect,
    })

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _run_persona_pipeline(
                    self, task_id, id_buyer_persona, n_variations,
                    photography_effect, id_product, custom_prompt
                )
            )
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception as sg_exc:
                logger.warning(f"[{task_id}] shutdown_asyncgens error (ignored): {sg_exc}")
            loop.close()
            asyncio.set_event_loop(None)

        logger.info(f"[{task_id}] PersonaPipeline complete")
        return result
    except Exception as exc:
        from celery.exceptions import MaxRetriesExceededError
        tb = traceback.format_exc()
        logger.error(
            f"[{task_id}] PersonaPipeline failed (attempt {self.request.retries + 1}): "
            f"{type(exc).__name__}: {exc}\n{tb}"
        )
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            logger.error(f"[{task_id}] Max retries exhausted. {type(exc).__name__}: {exc}")
            raise


# ---------------------------------------------------------------------------
# Async pipeline runner
# ---------------------------------------------------------------------------

@observe(name="fury.persona_image_pipeline")
async def _run_persona_pipeline(
    task,
    task_id: str,
    id_buyer_persona: int,
    n_variations: int,
    photography_effect: str,
    id_product: int | None = None,
    custom_prompt: str | None = None,
) -> dict:
    """Python-driven sequential persona image pipeline.

    Agents are created fresh on each job via lazy factories so that
    model/instruction changes in Langfuse take effect without worker restarts.
    """
    from agents.persona_data_collector_agent import make_persona_data_collector_agent
    from agents.persona_prompter_agent import make_persona_prompter_agent
    from agents.persona_auditor_agent import make_persona_auditor_agent
    from agents.nano_banana_agent import generate_images_from_prompts
    from services.persona_validators import (
        validate_persona_data_collector_response,
        validate_persona_prompter_response,
        validate_persona_auditor_response,
    )

    if settings.USE_MOCK_SINERGIA:
        from agents.tools.mock_sinergia import upload_persona_main_image
    else:
        from agents.tools.campaign_tools import upload_persona_main_image

    persona_data_collector = make_persona_data_collector_agent()
    persona_prompter       = make_persona_prompter_agent(custom_prompt)
    persona_auditor        = make_persona_auditor_agent()

    def _progress(step: str, detail: str = ""):
        if task is not None:
            task.update_state(state="PROGRESS", meta={"step": step, "detail": detail})
        logger.info(f"[{task_id}] → {step} {detail}")

    # ── STEP 1: Data Collection ──────────────────────────────────────────────
    _progress("data_collection", f"persona={id_buyer_persona}")
    persona_context = _load(_cp_key(task_id, "data"))
    if persona_context:
        logger.info(f"[{task_id}] checkpoint hit: data")
    else:
        collector_input = (
            f"id_buyer_persona={id_buyer_persona} "
            f"n_variations={n_variations} "
            f"photography_effect={photography_effect} "
            f"id_product={id_product if id_product else 0}"
        )
        # Manejar excepciones de validación para que no rompan el pipeline completo
        try:
            raw = await _run_agent(
                persona_data_collector,
                f"persona_{id_buyer_persona}_data",
                collector_input,
                validator=validate_persona_data_collector_response,
            )
        except AgentValidationError as ave:
            logger.error(f"[{task_id}] Data Collector validation failed: {ave.errors} — using empty context")
            raw = {}  # fallback to empty JSON object
            _progress("failed", f"persona={id_buyer_persona}")
            raise ave  # re-raise to trigger retry with exponential backoff
        
        
        # Si el validador retorna datos transformados, usarlos
        persona_context = raw # _parse_json_response(raw)
        if not isinstance(persona_context, dict):
            persona_context = {}
        _store(_cp_key(task_id, "data"), persona_context, ex=_CHECKPOINT_TTL)
    logger.info(f"[{task_id}] data_collector done — persona={id_buyer_persona}")

    # ── STEP 2 + STEP 3: Prompt Generation → Audit Gate (retry loop) ─────────
    MAX_AUDIT_RETRIES = 3
    audit_iteration = 0
    audit_result = {}
    final_prompts_data = {}
    final_variations_prompts = []

    while audit_iteration < MAX_AUDIT_RETRIES:
        audit_iteration += 1

        # ── STEP 2: Prompt Generation ────────────────────────────────────────
        _progress("prompt_generation", f"persona={id_buyer_persona} n={n_variations} attempt={audit_iteration}")

        # On first attempt use checkpoint; on retries always regenerate failing subset
        if audit_iteration == 1:
            prompts_data = _load(_cp_key(task_id, "prompts"))
        else:
            prompts_data = None  # force regeneration on retry

        if prompts_data and audit_iteration == 1:
            logger.info(f"[{task_id}] checkpoint hit: prompts")
        else:
            failing_ids = set(audit_result.get("variations_to_regenerate", []))

            if audit_iteration == 1 or not failing_ids:
                # First attempt — generate all variations
                prompter_input = (
                    f"Generate {n_variations} persona image variation prompts.\n"
                    f"Context:\n{json.dumps(persona_context, ensure_ascii=False)}"
                )
            else:
                # Retry — only regenerate failing variations, preserve passing ones
                _progress(
                    "retry_prompt_generation",
                    f"persona={id_buyer_persona} regenerating {len(failing_ids)} variations attempt={audit_iteration}"
                )
                audit_issues = audit_result.get("issues", [])
                failing_issues_text = json.dumps(
                    [i for i in audit_issues if i.get("variation_id") in failing_ids],
                    ensure_ascii=False,
                )
                prompter_input = (
                    f"Regenerate ONLY these failing variations: {sorted(failing_ids)}.\n"
                    f"The following hallucination issues were found — fix ALL of them:\n"
                    f"{failing_issues_text}\n"
                    f"Original context (ground truth — do NOT invent anything outside this):\n"
                    f"{json.dumps(persona_context, ensure_ascii=False)}"
                )

            # Manejar excepciones de validación para que no rompan el pipeline completo
            try:
                raw = await _run_agent(
                    persona_prompter,
                    f"persona_{id_buyer_persona}_prompts_a{audit_iteration}",
                    prompter_input,
                    validator=validate_persona_prompter_response,
                )
            except AgentValidationError as ave:
                logger.error(f"[{task_id}] Prompter validation failed: {ave.errors} — using empty prompts")
                raw = {}  # fallback to empty JSON object
                _progress("failed", f"persona={id_buyer_persona}")
                raise ave  # re-raise to trigger retry with exponential backoff

            regenerated = raw # _parse_json_response(raw)
            if not isinstance(regenerated, dict):
                regenerated = {}

            if audit_iteration == 1:
                # First attempt: use as-is
                prompts_data = regenerated
                _store(_cp_key(task_id, "prompts"), prompts_data, ex=_CHECKPOINT_TTL)
            else:
                # Merge: replace only the failing variations, keep passing ones
                new_variations = regenerated.get("variations", [])
                existing_vars = {v["plan_id"]: v for v in final_variations_prompts}
                for v in new_variations:
                    if v.get("plan_id") in failing_ids:
                        existing_vars[v["plan_id"]] = v
                prompts_data = {
                    "master_prompt": regenerated.get("master_prompt") or final_prompts_data.get("master_prompt", ""),
                    "photography_effect": photography_effect,
                    "variations": list(existing_vars.values()),
                }

        final_prompts_data = prompts_data
        final_variations_prompts = prompts_data.get("variations", [])
        logger.info(
            f"[{task_id}] persona_prompter done — attempt={audit_iteration} variations={len(final_variations_prompts)}"
        )

        # ── STEP 3: Audit Gate ───────────────────────────────────────────────
        _progress("audit", f"persona={id_buyer_persona} attempt={audit_iteration}")
        audit_input = json.dumps(
            {
                "persona_context": persona_context,
                "prompts_data": final_prompts_data,
            },
            ensure_ascii=False,
        )
        audit_raw = await _run_agent(
            persona_auditor,
            f"persona_{id_buyer_persona}_audit_a{audit_iteration}",
            audit_input,
            validator=validate_persona_auditor_response,
        )
        audit_result = _parse_json_response(audit_raw)
        if not isinstance(audit_result, dict):
            audit_result = {"overall_pass": True, "issues": [], "variations_to_regenerate": []}

        overall_pass = audit_result.get("overall_pass", True)
        issues_count = len(audit_result.get("issues", []))
        logger.info(
            f"[{task_id}] auditor done — attempt={audit_iteration} pass={overall_pass} issues={issues_count}"
        )

        if overall_pass:
            logger.info(f"[{task_id}] ✅ Audit passed on attempt {audit_iteration}")
            break

        if audit_iteration >= MAX_AUDIT_RETRIES:
            logger.warning(
                f"[{task_id}] ⚠️ Max audit retries ({MAX_AUDIT_RETRIES}) reached — "
                f"proceeding with best available prompts. Unresolved issues: {issues_count}"
            )
            break

        failing_ids = audit_result.get("variations_to_regenerate", [])
        if not failing_ids:
            logger.info(f"[{task_id}] No variations flagged for regeneration — treating as pass")
            break

        logger.info(
            f"[{task_id}] 🔄 Audit failed — retrying {len(failing_ids)} variations: {failing_ids}"
        )

    master_prompt = final_prompts_data.get("master_prompt", "")
    variations_prompts = final_variations_prompts

    # ── STEP 4: Image Generation (NanoBanana reused) ─────────────────────────
    _progress("image_generation", f"persona={id_buyer_persona} variations={len(variations_prompts)}")
    generated_images = []
    try:
        result = await generate_images_from_prompts(variations_prompts, id_buyer_persona, upload_image_to_library=False)
        generated_images = result.get("generated_images", [])
    except Exception as img_exc:
        logger.error(f"[{task_id}] image generation failed: {img_exc}")
    logger.info(f"[{task_id}] image_generation done — images={len(generated_images)}")

    ###########################################

    if settings.DEBUG and generated_images:
            import base64, os
            out_dir = "/tmp/fury_images"
            os.makedirs(out_dir, exist_ok=True)
            for img in generated_images:
                plan_id = img.get("plan_id", "unknown")
                for a_url in img.get("image_prompts", []):
                    url = a_url.get("image_url", "")
                    if url and url.startswith("data:"):
                        try:
                            _, b64data = url.split(",", 1)
                            img_bytes = base64.b64decode(b64data)
                            path = f"{out_dir}/{task_id[:8]}_{plan_id}_{a_url.get('element_id', 'no-id')}.jpg"
                            with open(path, "wb") as f:
                                f.write(img_bytes)
                            logger.info(f"[DEV] Saved image → {path}")
                        except Exception as e:
                            logger.warning(f"[DEV] Could not save image for plan={plan_id}: {e}")

    ###########################################

    # ── STEP 5: Upload to Sinergia Library (best-effort) ─────────────────────
    _progress("upload", f"persona={id_buyer_persona} images={len(generated_images)}")
    variations_out = []
    for gen in generated_images:
        variation_id = gen.get("plan_id", "")
        image_prompts = gen.get("image_prompts", [])
        diversity_axes = {}

        # Recover diversity_axes from the final approved prompts
        for v in variations_prompts:
            if v.get("plan_id") == variation_id:
                if image_prompts:
                    diversity_axes = image_prompts[0].get("diversity_axes", {})
                break

        # For persona portraits there is one image_prompts entry per variation
        for item in image_prompts:
            image_url = item.get("image_url")
            image_mime = item.get("image_mime_type", "image/png")
            image_prompt = item.get("image_prompt", "")
            image_id = ""

            if image_url:
                try:
                    upload_result = await upload_persona_main_image(
                        id_buyer_persona,
                        {
                            "image_data": image_url,
                            "image_name": f"persona_{id_buyer_persona}_{variation_id}",
                            "mime_type": image_mime,
                            "image_prompt": image_prompt
                        },
                    )
                    image_id = upload_result or ""
                    logger.info(
                        f"[{task_id}] uploaded persona image variation={variation_id} image_id={image_id}"
                    )
                except Exception as up_exc:
                    logger.error(
                        f"[{task_id}] upload failed variation={variation_id}: {up_exc} (ignored)"
                    )

            variations_out.append({
                "variation_id": variation_id,
                "diversity_axes": diversity_axes,
                "image_prompt": item.get("image_prompt", ""),
                "image_url": image_url,
                "image_id": image_id or None,
                "image_mime_type": image_mime,
            })

    # ── STEP 6: Assemble Final Result ─────────────────────────────────────────
    _progress("done", f"persona={id_buyer_persona}")
    return {
        "task_id": task_id,
        "id_buyer_persona": id_buyer_persona,
        "photography_effect": photography_effect,
        "master_prompt": master_prompt,
        "variations": variations_out,
        "audit_report": {
            "overall_pass": audit_result.get("overall_pass", True),
            "iterations": audit_iteration,
            "issues": audit_result.get("issues", []),
            "audit_notes": audit_result.get("audit_notes", ""),
        },
        "status": "DONE",
    }


# ---------------------------------------------------------------------------
# Edit Persona Main Image Pipeline
# ---------------------------------------------------------------------------

@celery_app.task(
    name="services.persona_job_runner_service.run_edit_persona_main_image_pipeline",
    bind=True,
    max_retries=3,
)
def run_edit_persona_main_image_pipeline(
    self,
    id_buyer_persona: int,
    n_variations: int = 4,
    photography_effect: str = "natural",
    id_product: int | None = None,
    custom_prompt: str | None = None,
    id_base_image: str | None = None,
    reference_images: list[str] | None = None,
    save_as: str = "main",
    label: str | None = None,
    visual_style: str | None = None,
):
    """Run the complete persona image editing pipeline as a Celery task.

    ``save_as="variant"`` saves the edit as a variant of ``id_base_image`` (the
    independent variant editor); ``"main"`` (default) saves as a main image.
    """
    task_id = self.request.id
    logger.info(
        f"[{task_id}] ▶ EditPersonaMainImagePipeline start — "
        f"persona={id_buyer_persona} n={n_variations} effect={photography_effect} "
        f"base_image={id_base_image}"
    )

    self.update_state(state="PROGRESS", meta={
        "step": "starting",
        "id_buyer_persona": id_buyer_persona,
        "n_variations": n_variations,
        "photography_effect": photography_effect,
        "id_base_image": id_base_image,
    })

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _run_edit_persona_main_image_pipeline(
                    self, task_id, id_buyer_persona, n_variations,
                    photography_effect, id_product, custom_prompt,
                    id_base_image, reference_images, save_as=save_as,
                    label=label, visual_style=visual_style
                )
            )
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception as sg_exc:
                logger.warning(f"[{task_id}] shutdown_asyncgens error (ignored): {sg_exc}")
            loop.close()
            asyncio.set_event_loop(None)

        logger.info(f"[{task_id}] EditPersonaMainImagePipeline complete")
        return result
    except Exception as exc:
        from celery.exceptions import MaxRetriesExceededError
        tb = traceback.format_exc()
        logger.error(
            f"[{task_id}] EditPersonaMainImagePipeline failed (attempt {self.request.retries + 1}): "
            f"{type(exc).__name__}: {exc}\n{tb}"
        )
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            logger.error(f"[{task_id}] Max retries exhausted. {type(exc).__name__}: {exc}")
            raise


@observe(name="fury.edit_persona_main_image_pipeline")
async def _run_edit_persona_main_image_pipeline(
    task,
    task_id: str,
    id_buyer_persona: int,
    n_variations: int,
    photography_effect: str,
    id_product: int | None = None,
    custom_prompt: str | None = None,
    id_base_image: str | None = None,
    reference_images: list[str] | None = None,
    save_as: str = "main",
    label: str | None = None,
    visual_style: str | None = None,
) -> dict:
    """Python-driven sequential persona main image editing pipeline.

    ``save_as`` controls where the edited result lands:
      - "main"    → saved as a persona MAIN image (default, unchanged behaviour)
      - "variant" → saved as a VARIANT attached to ``id_base_image`` (the variant
                    editor — independent of the main-image editor)
    
    Pipeline steps:
      1. DataCollector — fetches buyer persona + product + base image info
      2. NanoBanana2 — edits base image via Gemini with custom_prompt + references
      3. Prompter — analyzes variations and generates descriptive prompts
      4. UploadImages — uploads images to Sinergia library
      5. Result — assembles final result
    """
    from agents.persona_data_collector_agent import make_persona_data_collector_agent
    from agents.edit_prompter_agent import make_edit_prompter_agent
    from agents.nano_banana_agent import generate_images_from_prompts
    from services.persona_validators import (
        validate_persona_data_collector_response,
        validate_edit_prompter_response,
    )

    if settings.USE_MOCK_SINERGIA:
        from agents.tools.mock_sinergia import (
            get_buyer_persona_context,
            get_product_context,
            get_image_from_library,
            get_persona_variant_image,
            get_person_main_image,
            upload_persona_main_image,
            upload_persona_image_variant,
        )
    else:
        from agents.tools.campaign_tools import (
            get_buyer_persona_context,
            get_product_context,
            get_image_from_library,
            get_persona_variant_image,
            get_person_main_image,
            upload_persona_main_image,
            upload_persona_image_variant,
        )

    if save_as == "variant" and not id_base_image:
        raise ValueError("save_as='variant' requires id_base_image (the variant to edit).")

    persona_data_collector = make_persona_data_collector_agent()
    edit_prompter = make_edit_prompter_agent()

    def _progress(step: str, detail: str = ""):
        if task is not None:
            task.update_state(state="PROGRESS", meta={"step": step, "detail": detail})
        logger.info(f"[{task_id}] → {step} {detail}")

    # ── STEP 1: Data Collection ──────────────────────────────────────────────
    _progress("data_collection", f"persona={id_buyer_persona}")
    
    # Get buyer persona context
    collector_input = (
        f"id_buyer_persona={id_buyer_persona} "
        f"n_variations={n_variations} "
        f"photography_effect={photography_effect} "
        f"id_product={id_product if id_product else 0}"
    )
    raw = await _run_agent(
        persona_data_collector,
        f"edit_persona_{id_buyer_persona}_data",
        collector_input,
        validator=validate_persona_data_collector_response,
    )
    persona_context = _parse_json_response(raw)
    if not isinstance(persona_context, dict):
        persona_context = {}
    
    # Get base image info. For a variant edit the base is a variant image, so resolve it
    # by ID from the library (works for any image) rather than the main-image getter —
    # otherwise the base wouldn't be found and the edit would generate from scratch.
    base_image_info = None
    if id_base_image:
        try:
            if save_as == "variant":
                base_image_data = await get_persona_variant_image(id_buyer_persona, id_base_image)
            else:
                base_image_data = await get_person_main_image(id_buyer_persona, id_base_image)
            base_image_info = {
                "id": id_base_image,
                "url": base_image_data.get("url") if isinstance(base_image_data, dict) else None,
                "prompt": base_image_data.get("prompt") if isinstance(base_image_data, dict) else None,
            }
        except Exception as img_exc:
            logger.warning(f"[{task_id}] Failed to get base image {id_base_image}: {img_exc}")

    # Combine context with base image info
    data_collector_output = {
        **persona_context,
        "base_image": base_image_info,
        #"reference_images": reference_images or [],
    }
    
    _store(_cp_key(task_id, "data"), data_collector_output, ex=_CHECKPOINT_TTL)
    logger.info(f"[{task_id}] data_collector done — persona={id_buyer_persona}")

    # ── STEP 2: Image Editing via NanoBanana2 ────────────────────────────────
    _progress("image_editing", f"persona={id_buyer_persona} n={n_variations}")

    final_visual_style = visual_style if visual_style else "photorealistic edit"
    
    # Prepare editing prompts for each variation
    editing_prompts = []
    for i in range(n_variations):
        variation_prompt = {
            "plan_id": f"v{i+1}",
            "image_prompts": [{
                "element_id": f"edit_v{i+1}",
                "element_type": "image",
                "image_request": {
                    "setting": "edit_base_image",
                    "composition": {
                        "framing": "original",
                        "layout_dynamics": {"rule_of_thirds": {}}
                    },
                    "lighting": {
                        "type": photography_effect,
                        "effect": "preserve_original_lighting"
                    },
                    "technical_specs": {
                        "style": final_visual_style,
                        "quality": "Cinematic 8k",
                        "aspect_ratio": "4:5",
                        "effect": "No visual margins or borders"
                    }
                },
                "image_prompt": (
                    f"Acts as a binary image editor, edit the base image according to these instructions: {custom_prompt}\n"
                    f"Photography effect: {photography_effect}\n"
                    f"Visual style: {final_visual_style}\n"
                ),
                "visual_style": final_visual_style,
                "diversity_axes": {
                    "setting": "edit_base_image",
                    "emotional_beat": "preserved",
                    "camera_angle": "original",
                    "time_of_day": "original",
                    "outfit_style": "original"
                }
            }],
            "product_image_urls": persona_context.get("product", {}).get("image_urls", []),
            "base_image_url": base_image_info.get("url") if base_image_info else None,
            "reference_images": reference_images or [],
        }
        editing_prompts.append(variation_prompt)
    
    # Generate edited images
    generated_images = []
    try:
        result = await generate_images_from_prompts(editing_prompts, id_buyer_persona, upload_image_to_library=False)
        generated_images = result.get("generated_images", [])
    except Exception as img_exc:
        logger.error(f"[{task_id}] image editing failed: {img_exc}")
    logger.info(f"[{task_id}] image_editing done — images={len(generated_images)}")


    ###########################################

    if settings.DEBUG and generated_images:
            import base64, os
            out_dir = "/tmp/fury_images"
            os.makedirs(out_dir, exist_ok=True)
            for img in generated_images:
                plan_id = img.get("plan_id", "unknown")
                for a_url in img.get("image_prompts", []):
                    url = a_url.get("image_url", "")
                    if url and url.startswith("data:"):
                        try:
                            _, b64data = url.split(",", 1)
                            img_bytes = base64.b64decode(b64data)
                            path = f"{out_dir}/{task_id[:8]}_{plan_id}_{a_url.get('element_id', 'no-id')}.jpg"
                            with open(path, "wb") as f:
                                f.write(img_bytes)
                            logger.info(f"[DEV] Saved image → {path}")
                        except Exception as e:
                            logger.warning(f"[DEV] Could not save image for plan={plan_id}: {e}")

    ###########################################

    # ── STEP 3: Prompter — Analyze and Describe Variations ────────────────────
    _progress("prompt_analysis", f"persona={id_buyer_persona} n={len(generated_images)}")
    
    analyzed_variations = []
    for gen in generated_images:
        variation_id = gen.get("plan_id", "")
        image_prompts = gen.get("image_prompts", [])
        
        for item in image_prompts:
            image_url = item.get("image_url")
            image_mime_type = item.get("image_mime_type", "image/png")
                        
            if image_url:
                # Prepare text prompt with context
                prompter_text = (
                    f"Analyze this persona image and generate a descriptive prompt.\n"
                    f"Original custom prompt: {custom_prompt or 'none'}\n"
                    f"Photography effect: {photography_effect}\n"
                    f"Visual style: {final_visual_style}\n"
                    f"Base image ID: {id_base_image or 'not provided'}"
                )
                
                raw_prompt = await _run_agent(
                    edit_prompter,
                    f"edit_persona_{id_buyer_persona}_prompt_{variation_id}",
                    prompter_text,
                    image_data=image_url,  # Pass image as base64 data URI
                    image_mime_type=image_mime_type,  # Pass mime type explicitly
                    validator=validate_edit_prompter_response,
                )
                
                analyzed_variations.append({
                    "variation_id": variation_id,
                    "image_url": image_url,
                    "image_prompt": raw_prompt.strip() if raw_prompt else item.get("image_prompt", ""),
                    "image_mime_type": item.get("image_mime_type", "image/png"),
                })
    
    logger.info(f"[{task_id}] prompt_analysis done — variations={len(analyzed_variations)}")

    # ── STEP 4: Upload to Sinergia Library (best-effort) ─────────────────────
    _progress("upload", f"persona={id_buyer_persona} images={len(analyzed_variations)}")
    variations_out = []
    
    for var in analyzed_variations:
        image_url = var.get("image_url")
        image_prompt = var.get("image_prompt", "")
        image_mime = var.get("image_mime_type", "image/png")
        variation_id = var.get("variation_id", "")
        image_id = ""

        if image_url:
            payload = {
                "image_data": image_url,
                "image_name": f"persona_{id_buyer_persona}_{variation_id}_edited",
                "mime_type": image_mime,
                "image_prompt": image_prompt,
            }
            try:
                if save_as == "variant":
                    # Independent variant editor: save the edited image as a VARIANT
                    # attached to the base image being edited — NOT as a main image.
                    upload_result = await upload_persona_image_variant(
                        id_buyer_persona, id_base_image, payload, label,
                    )
                else:
                    upload_result = await upload_persona_main_image(
                        id_buyer_persona, payload,
                    )
                image_id = upload_result or ""
                logger.info(
                    f"[{task_id}] uploaded edited persona {save_as} variation={variation_id} image_id={image_id}"
                )
            except Exception as up_exc:
                logger.error(
                    f"[{task_id}] upload failed variation={variation_id}: {up_exc} (ignored)"
                )

        variations_out.append({
            "variation_id": variation_id,
            "image_prompt": image_prompt,
            #"image_url": image_url,
            #"image_id": image_id or None,
            "image_mime_type": image_mime,
        })

    # ── STEP 5: Assemble Final Result ─────────────────────────────────────────
    _progress("done", f"persona={id_buyer_persona}")
    return {
        "task_id": task_id,
        "id_buyer_persona": id_buyer_persona,
        "photography_effect": photography_effect,
        "id_base_image": id_base_image,
        #"reference_images": reference_images or [],
        "custom_prompt": custom_prompt,
        "variations": variations_out,
        "status": "DONE",
    }


# ---------------------------------------------------------------------------
# Persona Image Variations Pipeline
# ---------------------------------------------------------------------------

@celery_app.task(
    name="services.persona_job_runner_service.run_generate_persona_image_variations_pipeline",
    bind=True,
    max_retries=3,
)
def run_generate_persona_image_variations_pipeline(
    self,
    id_buyer_persona: int,
    id_base_image: str,
    id_product: int | None = None,
):
    """Run the complete persona image variations pipeline as a Celery task."""
    task_id = self.request.id
    logger.info(
        f"[{task_id}] ▶ PersonaImageVariationsPipeline start — "
        f"persona={id_buyer_persona} base_image={id_base_image} product={id_product}"
    )

    self.update_state(state="PROGRESS", meta={
        "step": "starting",
        "id_buyer_persona": id_buyer_persona,
        "id_base_image": id_base_image,
        "id_product": id_product,
    })

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _run_generate_persona_image_variations_pipeline(
                    self, task_id, id_buyer_persona, id_base_image, id_product
                )
            )
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception as sg_exc:
                logger.warning(f"[{task_id}] shutdown_asyncgens error (ignored): {sg_exc}")
            loop.close()
            asyncio.set_event_loop(None)

        logger.info(f"[{task_id}] PersonaImageVariationsPipeline complete")
        return result
    except Exception as exc:
        from celery.exceptions import MaxRetriesExceededError
        tb = traceback.format_exc()
        logger.error(
            f"[{task_id}] PersonaImageVariationsPipeline failed (attempt {self.request.retries + 1}): "
            f"{type(exc).__name__}: {exc}\n{tb}"
        )
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            logger.error(f"[{task_id}] Max retries exhausted. {type(exc).__name__}: {exc}")
            raise


@observe(name="fury.persona_image_variations_pipeline")
async def _run_generate_persona_image_variations_pipeline(
    task,
    task_id: str,
    id_buyer_persona: int,
    id_base_image: str,
    id_product: int | None = None,
) -> dict:
    """Python-driven sequential persona image variations pipeline.
    
    Pipeline steps:
      1. DataCollector — fetches buyer persona + base image info
      2. Prompt Generation — generates 5 variant prompts (Frontal, Side Face, Expression, Full Body, Outfit)
      3. Image Generation — generates variations via NanoBanana2
      4. UploadImages — uploads images to Sinergia library
      5. Result — assembles final result
    """
    from agents.persona_data_collector_agent import make_persona_data_collector_agent
    from agents.persona_variants_prompter_agent import make_persona_variants_prompter_agent
    from agents.nano_banana_agent import generate_images_from_prompts
    from services.persona_validators import (
        validate_persona_data_collector_response,
        validate_persona_variants_prompter_response,
    )

    if settings.USE_MOCK_SINERGIA:
        from agents.tools.mock_sinergia import (
            get_buyer_persona_context,
            get_person_main_image,
            upload_persona_image_variant,
        )
    else:
        from agents.tools.campaign_tools import (
            get_buyer_persona_context,
            get_person_main_image,
            upload_persona_image_variant,
        )

    persona_data_collector = make_persona_data_collector_agent()
    variants_prompter = make_persona_variants_prompter_agent()

    def _progress(step: str, detail: str = ""):
        if task is not None:
            task.update_state(state="PROGRESS", meta={"step": step, "detail": detail})
        logger.info(f"[{task_id}] → {step} {detail}")

    # ── STEP 1: Data Collection ──────────────────────────────────────────────
    _progress("data_collection", f"persona={id_buyer_persona}")
    
    # Get buyer persona context
    collector_input = (
        f"id_buyer_persona={id_buyer_persona} "
        f"id_product={id_product} "
        f"id_base_image={id_base_image}"
    )
    raw = await _run_agent(
        persona_data_collector,
        f"variants_persona_{id_buyer_persona}_data",
        collector_input,
        validator=validate_persona_data_collector_response,
    )
    persona_context = _parse_json_response(raw)
    if not isinstance(persona_context, dict):
        persona_context = {}
    
    # Get base image info
    base_image_info = None
    if id_base_image:
        try:
            base_image_data = await get_person_main_image(id_buyer_persona, id_base_image)
            base_image_info = {
                "id": id_base_image,
                "url": base_image_data.get("url") if isinstance(base_image_data, dict) else None,
                "prompt": base_image_data.get("prompt") if isinstance(base_image_data, dict) else None,
            }
        except Exception as img_exc:
            logger.warning(f"[{task_id}] Failed to get base image {id_base_image}: {img_exc}")
    
    # Combine context with base image info
    data_collector_output = {
        **persona_context,
        "base_image": base_image_info,
    }
    
    _store(_cp_key(task_id, "data"), data_collector_output, ex=_CHECKPOINT_TTL)
    logger.info(f"[{task_id}] data_collector done — persona={id_buyer_persona}")

    # ── STEP 2: Prompt Generation (5 variants) ───────────────────────────────
    _progress("prompt_generation", f"persona={id_buyer_persona}")
    
    # Prepare context for prompter
    prompter_context = {
        "buyer_persona": persona_context.get("buyer_persona", {}),
        "product": persona_context.get("product", {}),
        "base_image_prompt": base_image_info.get("prompt") if base_image_info else "",
    }
    
    prompter_input = json.dumps(prompter_context, ensure_ascii=False)
    
    raw_prompts = await _run_agent(
        variants_prompter,
        f"variants_persona_{id_buyer_persona}_prompts",
        prompter_input,
        validator=validate_persona_variants_prompter_response,
    )
    
    variants_data = _parse_json_response(raw_prompts)
    if not isinstance(variants_data, dict):
        variants_data = {"variants": []}
    # Normalize the array key: the agent may emit "variants" (per its instruction) or
    # the legacy "variations"; everything downstream reads "variants".
    if not variants_data.get("variants") and variants_data.get("variations"):
        variants_data["variants"] = variants_data["variations"]

    _store(_cp_key(task_id, "prompts"), variants_data, ex=_CHECKPOINT_TTL)
    logger.info(f"[{task_id}] prompt_generation done — variants={len(variants_data.get('variants', []))}")

    # ── STEP 3: Image Generation (NanoBanana2) ───────────────────────────────
    _progress("image_generation", f"persona={id_buyer_persona}")
    
    # Extract variations prompts for NanoBanana
    variations_prompts = variants_data.get("variants", [])
    
    generated_images = []
    try:
        result = await generate_images_from_prompts(variations_prompts, id_buyer_persona, upload_image_to_library=False)
        generated_images = result.get("generated_images", [])
    except Exception as img_exc:
        logger.error(f"[{task_id}] image generation failed: {img_exc}")
    logger.info(f"[{task_id}] image_generation done — images={len(generated_images)}")

    ###########################################

    if settings.DEBUG and generated_images:
            import base64, os
            out_dir = "/tmp/fury_images"
            os.makedirs(out_dir, exist_ok=True)
            for img in generated_images:
                plan_id = img.get("plan_id", "unknown")
                for a_url in img.get("image_prompts", []):
                    url = a_url.get("image_url", "")
                    if url and url.startswith("data:"):
                        try:
                            _, b64data = url.split(",", 1)
                            img_bytes = base64.b64decode(b64data)
                            path = f"{out_dir}/{task_id[:8]}_{plan_id}_{a_url.get('element_id', 'no-id')}.jpg"
                            with open(path, "wb") as f:
                                f.write(img_bytes)
                            logger.info(f"[DEV] Saved image → {path}")
                        except Exception as e:
                            logger.warning(f"[DEV] Could not save image for plan={plan_id}: {e}")

    ###########################################

    # ── STEP 4: Upload to Sinergia Library (best-effort) ─────────────────────
    _progress("upload", f"persona={id_buyer_persona} images={len(generated_images)}")
    variations_out = []
    
    for gen in generated_images:
        variation_id = gen.get("plan_id", "")
        variant_type = gen.get("variant_type", "")
        image_prompts = gen.get("image_prompts", [])
        
        for item in image_prompts:
            image_url = item.get("image_url")
            image_mime_type = item.get("image_mime_type", "image/png")
            image_prompt = item.get("image_prompt", "")
            image_id = ""

            if image_url:
                try:
                    upload_result = await upload_persona_image_variant(
                        id_buyer_persona,
                        id_base_image,
                        {
                            "image_data": image_url,
                            "image_name": f"persona_{id_buyer_persona}_{variation_id}_variant",
                            "mime_type": image_mime_type,
                            "image_prompt": image_prompt,
                            "label": variant_type
                        },
                    )
                    image_id = upload_result or ""
                    logger.info(
                        f"[{task_id}] uploaded persona variant={variation_id} image_id={image_id}"
                    )
                except Exception as up_exc:
                    logger.error(
                        f"[{task_id}] upload failed variation={variation_id}: {up_exc} (ignored)"
                    )

            variations_out.append({
                "variation_id": variation_id,
                "variant_type": gen.get("variant_type", ""),
                "image_prompt": image_prompt,
                "image_url": image_url,
                "image_id": image_id or None,
                "image_mime_type": image_mime_type,
            })

    # ── STEP 5: Assemble Final Result ─────────────────────────────────────────
    _progress("done", f"persona={id_buyer_persona}")
    return {
        "task_id": task_id,
        "id_buyer_persona": id_buyer_persona,
        "id_base_image": id_base_image,
        "id_product": id_product,
        "master_prompt": variants_data.get("master_prompt", ""),
        "base_image_prompt": variants_data.get("base_image_prompt", ""),
        "variations": variations_out,
        "status": "DONE",
    }
