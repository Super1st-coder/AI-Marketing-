"""Unit tests for steps 6–10 of the Diversity_Path
(`job_runner_service._finish_diversity_ad` and the `_AdDiversityFailure` capture in
`_run_diversity_ad`; adset-creative-diversity, task 11.5; Req 5.9, 8.1–8.5, 8.7, 11.7).

Runs the real functions on top of FakeRedis and in-memory async fakes: no network,
Redis or LLM.

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_finish.py
"""
import asyncio
import json

import pytest

import services.job_runner_service as jrs
from services.adset_diversity import DEFAULT_DECORATIVE_IMAGE_PATTERNS, build_variant_slots
from tests._diversity_pipeline_fakes import FakeGetATemplateDefinition, FakeRedis

TASK_ID = "task-finish"
ID_ADSET = 7
AD_ID = 101
PLAN_ID = f"plan_ad_{AD_ID}"
TEMPLATES = ["tA", "tB", "tC"]
OLD_VARIANTS = [11, 12]


def _slots(n):
    return build_variant_slots(PLAN_ID, ad_slot=0, n_variants=n, project_templates=TEMPLATES)


def _copy(slot):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "headline": [f"H {slot['variant_key']}"],
        "template_elements": [{"element_id": "title", "text": f"H {slot['variant_key']}"}],
    }


def _prompt(slot):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "image_prompts": [{"element_id": "img", "image_prompt": "p", "image_request": "r"}],
    }


class _Recorder:
    """Shared ordered log of calls made by the fakes below."""

    def __init__(self):
        self.events = []

    def names(self):
        return [name for name, _ in self.events]


def _make_deps(rec, *, images=None, images_exc=None, saved=True, abyssale=None, abyssale_exc=None):
    async def generate_images(prompts, ad_id):
        rec.events.append(("generate_images", [p["variant_key"] for p in prompts]))
        if images_exc:
            raise images_exc
        if images is not None:
            return {"ok": True, "generated_images": images}
        return {"ok": True, "generated_images": [
            {**p, "image_prompts": [{"element_id": "img", "image_url": "data:x", "image_id": "IMG"}]}
            for p in prompts
        ]}

    async def save_ads_programmatically(id_adset, ad_id, copies):
        rec.events.append(("save_ads", [c["variant_key"] for c in copies]))
        return [
            {"plan_id": c["plan_id"], "template_id": c["template_id"], "variant_key": c["variant_key"],
             "saved": saved, "ad_id": (900 + i) if saved else None}
            for i, c in enumerate(copies)
        ]

    def build_abyssale_payload(content, template_id, ratio):
        rec.events.append(("build_abyssale_payload", (len(content), template_id, ratio)))
        return jrs_build_abyssale_payload(content, template_id, ratio)

    async def post_to_abyssale_and_wait(task_id, payload, id_adset, ad_id):
        rec.events.append(("post_to_abyssale_and_wait", payload))
        if abyssale_exc:
            raise abyssale_exc
        return abyssale if abyssale is not None else {"ok": True, "batch_id": ["b1", "b2"]}

    async def delete_variants(ids):
        rec.events.append(("delete_variants", list(ids)))
        return True

    return jrs._DiversityDeps(
        get_template_context=None, delete_variants=delete_variants, validate_ctas=None,
        save_ads_programmatically=save_ads_programmatically, generate_images=generate_images,
        build_abyssale_payload=build_abyssale_payload,
        post_to_abyssale_and_wait=post_to_abyssale_and_wait,
        make_estratega_adset_agent=None, make_copywriter_agent=None,
        make_image_prompter_agent=None, make_validador_adset_agent=None, progress=lambda *_: None,
        template_definitions=jrs._JobTemplateDefinitions(
            FakeGetATemplateDefinition(), DEFAULT_DECORATIVE_IMAGE_PATTERNS),
    )


def jrs_build_abyssale_payload(content, template_id, ratio):
    from agents.tools.abyssale_tools import build_abyssale_payload
    return build_abyssale_payload(content, template_id, ratio)


def _job(*, add_variant=False, id_variant=OLD_VARIANTS, id_ad=AD_ID, n_variants=3):
    return jrs._DiversityJob(
        task=None, task_id=TASK_ID, id_adset=ID_ADSET, n_variants=n_variants,
        project_id="p", id_ad=id_ad, custom_prompt=None, add_variant=add_variant,
        id_variant=id_variant, adset_context={}, adset_context_json="{}",
    )


def _ad():
    ids = tuple(TEMPLATES)  # the template_ids of the case's slots
    return jrs._DiversityAdInput(ad_id=AD_ID, ad_slot=0, territory=None, all_territories=(), forbidden=(),
                                 templates=jrs._JobTemplates(ids, ids))


def _report():
    return {"ad_id": AD_ID, "plan_id": PLAN_ID, "deterministic_pass": True, "deterministic_errors": [],
            "deterministic_warnings": [], "overall_pass": True, "iterations": 1,
            "subset_to_regenerate": [], "ad_failed": False, "error": None}


@pytest.fixture
def redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(jrs, "_redis", lambda: fake)
    return fake


def _finish(deps, job, n=3, copies=None, prompts=None):
    slots = _slots(n)
    plan = {"id": PLAN_ID, "concept": "c", "variants": [dict(s) for s in slots]}
    # Shuffled on purpose: payloads must follow the Variant_Slot order (Req 8.1).
    copies = copies if copies is not None else [_copy(s) for s in reversed(slots)]
    prompts = prompts if prompts is not None else [_prompt(s) for s in reversed(slots)]
    verdict = {"overall_pass": True, "subset_to_regenerate": []}
    result = asyncio.run(jrs._finish_diversity_ad(
        deps, _ad(), job, plan, copies, prompts, _report(), verdict,
    ))
    return result, slots


def test_happy_path_saves_renders_and_replaces_old_variants(redis):
    rec = _Recorder()
    result, slots = _finish(_make_deps(rec), _job())
    keys = [s["variant_key"] for s in slots]

    assert rec.names() == [
        "generate_images", "save_ads", "build_abyssale_payload",
        "post_to_abyssale_and_wait", "delete_variants",
    ]
    assert dict(rec.events)["save_ads"] == keys
    assert dict(rec.events)["delete_variants"] == OLD_VARIANTS
    elements = dict(rec.events)["post_to_abyssale_and_wait"]["elements"]
    assert [e["template_id"] for e in elements] == [s["template_id"] for s in slots]  # Req 8.2
    assert [e["metadata"]["plan_id"] for e in elements] == keys
    assert [e["ad_channel_id"] for e in elements] == [900, 901, 902]
    assert dict(rec.events)["build_abyssale_payload"] == (3, slots[0]["template_id"], "4:5")

    assert [p["variant_key"] for p in result.proposals] == keys  # Req 5.9
    assert [s["variant_key"] for s in result.saved_ads] == keys
    assert result.abyssale_batch_id == ["b1", "b2"]
    assert result.validation_report["overall_pass"] is True
    assert result.diversity_report["ad_failed"] is False
    for bid in ("b1", "b2"):
        assert redis.get(f"fury:webhook:task:{bid}") == TASK_ID
    assert json.loads(redis.get(jrs._cp_key(TASK_ID, AD_ID, "saved_ads")))[0]["saved"] is True


def test_image_generator_exception_continues_with_empty_images(redis):
    rec = _Recorder()
    result, _ = _finish(_make_deps(rec, images_exc=RuntimeError("secret?X-Amz-Signature=abc")), _job())

    assert rec.names()[1:] == ["save_ads", "build_abyssale_payload", "post_to_abyssale_and_wait",
                               "delete_variants"]  # Req 11.7
    elements = dict(rec.events)["post_to_abyssale_and_wait"]["elements"]
    assert len(elements) == 3 and all(e["image_ids"] == [] for e in elements)
    assert result.abyssale_batch_id == ["b1", "b2"]


def test_saved_ads_checkpoint_is_reused(redis):
    rec = _Recorder()
    slots = _slots(2)
    cached = [{"plan_id": PLAN_ID, "template_id": s["template_id"], "variant_key": s["variant_key"],
               "saved": True, "ad_id": 500 + i} for i, s in enumerate(slots)]
    redis.set(jrs._cp_key(TASK_ID, AD_ID, "saved_ads"), json.dumps(cached))
    result, _ = _finish(_make_deps(rec), _job(n_variants=2), n=2)

    assert "save_ads" not in rec.names()
    assert result.saved_ads == cached
    assert rec.names()[-1] == "delete_variants"


@pytest.mark.parametrize("job_kwargs, deps_kwargs", [
    ({"add_variant": True}, {}),                                   # Req 8.4
    ({"id_variant": []}, {}),
    ({"id_ad": AD_ID + 1}, {}),
    ({}, {"saved": False}),                                        # Req 8.5
    ({}, {"abyssale_exc": RuntimeError("boom")}),                  # Req 8.7
    ({}, {"abyssale": {"ok": True, "batch_id": []}}),
    ({}, {"abyssale": {"ok": True, "batch_id": ""}}),
    ({}, {"abyssale": {"ok": True, "batch_id": None}}),
])
def test_delete_variants_skipped(redis, job_kwargs, deps_kwargs):
    rec = _Recorder()
    result, _ = _finish(_make_deps(rec, **deps_kwargs), _job(**job_kwargs))

    assert "delete_variants" not in rec.names()
    assert "post_to_abyssale_and_wait" in rec.names()
    if "abyssale_exc" in deps_kwargs or "abyssale" in deps_kwargs:
        assert result.abyssale_batch_id is None


def test_ad_diversity_failure_yields_failed_report_without_side_effects(monkeypatch, redis):
    rec = _Recorder()

    async def failing_plan(deps, ad, job):
        raise jrs._AdDiversityFailure(f"no templates for project_id=p ad_id={ad.ad_id}")

    monkeypatch.setattr(jrs, "_build_or_load_creative_plan", failing_plan)
    result = asyncio.run(jrs._run_diversity_ad(_make_deps(rec), _ad(), _job()))

    assert rec.events == []  # no images, save_ads, Abyssale nor delete_variants
    report = result.diversity_report
    assert report["ad_failed"] is True and report["overall_pass"] is False
    assert report["error"] == f"no templates for project_id=p ad_id={AD_ID}"
    assert result.saved_ads == [] and result.proposals == [] and result.abyssale_batch_id is None
