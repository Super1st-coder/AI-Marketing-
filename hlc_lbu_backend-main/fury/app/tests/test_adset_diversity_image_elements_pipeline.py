"""Pipeline-side defence in depth for Image_Elements (adset-creative-diversity, P15, D27).

Sections:
    * build_abyssale_payload text-layer protection (task 36.3; Property 34; Req 15.11).
    * Template_Definition resolution: per-Ad failure, job cache, mock adapter
      (task 41.1; Req 15.1, 15.3, 15.13, 12.33).
    * image_prompts Checkpoint, Image_Prompter retry and regeneration under the
      Image_Elements_Checker (task 41.2; Req 15.6, 15.8, 15.9, 12.31, 12.32).
    * _finish_diversity_ad filtering before the Image_Generator and the
      build_abyssale_payload `hook` case with the flag on/off (task 41.3; Req 15.10,
      15.11, 12.34).

Everything runs inside `network_guard()` with a loguru `LogCapture`: no network,
Redis, Sinergia, Abyssale or LLM.

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_image_elements_pipeline.py
    PYTHONPATH=. python -m tests.test_adset_diversity_image_elements_pipeline
"""
from __future__ import annotations

import asyncio
import copy
import json
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import services.job_runner_service as jrs
from agents.tools.abyssale_tools import build_abyssale_payload
from core.validation import AgentValidationError
from services.adset_diversity import (
    DEFAULT_DECORATIVE_IMAGE_PATTERNS,
    ImageElements,
    build_variant_slots,
    check_image_elements,
    check_variant_items,
)
from tests._diversity_pipeline_fakes import (
    COPYWRITER,
    ESTRATEGA_ADSET,
    IMAGE_PROMPTER,
    VALIDADOR_ADSET,
    FakeAgentFactories,
    FakeGetATemplateDefinition,
    FakeGetTemplateContext,
    FakeRedis,
    FakeRunAgent,
    LogCapture,
    conformant_image_prompts,
    cp_key,
    expected_image_elements,
    expected_template_order,
    image_elements_from_message,
    make_adset_context,
    mock_template_ids,
    mock_templates,
    network_guard,
    patched_diversity_pipeline,
)

SKIP_WARNING = "build_abyssale_payload: image skipped for text layer"
FORMAT_RATIO = "4:5"


# ---------------------------------------------------------------------------
# Strategies: creative_content entries for build_abyssale_payload
# ---------------------------------------------------------------------------

# Small shared id pool so text and image ids collide often.
_ELEMENT_IDS = st.sampled_from(["hook", "tagline", "cta", "product_image", "background", "img"])
_TEXTS = st.text(min_size=0, max_size=12)


@st.composite
def _text_element(draw) -> dict[str, Any]:
    el: dict[str, Any] = {"element_id": draw(_ELEMENT_IDS)}
    if draw(st.booleans()):  # `text` may be absent -> payload ""
        el["text"] = draw(_TEXTS)
    return el


@st.composite
def _image_prompt(draw, index: int) -> dict[str, Any]:
    prompt: dict[str, Any] = {
        "element_id": draw(_ELEMENT_IDS),
        "image_id": f"img-{index}",
        "prompt": "a prompt",
    }
    # With and without image_url (absent, None, "" or a real-looking URL).
    url = draw(st.sampled_from(["absent", None, "", "url"]))
    if url == "url":
        prompt["image_url"] = f"https://cdn.example/{index}.png?X-Amz-Signature=sig{index}"
    elif url != "absent":
        prompt["image_url"] = url
    return prompt


@st.composite
def _entry(draw, index: int) -> dict[str, Any]:
    if draw(st.integers(0, 9)) == 0:
        return {"error": f"plan {index} failed"}
    texts = draw(st.lists(_text_element(), max_size=5))
    n_images = draw(st.integers(0, 5))
    images = [draw(_image_prompt(index * 10 + i)) for i in range(n_images)]
    copy_part = {"template_id": f"tpl-{index}", "template_elements": texts}
    image_part = {"image_prompts": images}
    plan = {"id": f"plan-{index}"}
    ad_channel = {"ad_id": 100 + index}
    # Key order of the entry itself is also arbitrary.
    if draw(st.booleans()):
        return {"image": image_part, "copy": copy_part, "plan": plan, "ad_channel": ad_channel}
    return {"plan": plan, "copy": copy_part, "image": image_part, "ad_channel": ad_channel}


@st.composite
def creative_contents(draw) -> list[dict[str, Any]]:
    n = draw(st.integers(1, 4))
    return [draw(_entry(i)) for i in range(n)]


# ---------------------------------------------------------------------------
# Independent oracle
# ---------------------------------------------------------------------------


def _expected_entry(item: dict[str, Any]) -> tuple[dict, list, list[str]]:
    """(layers, image_ids, colliding element_ids with image_url) for one entry."""
    texts: dict[str, dict] = {}
    for el in item["copy"]["template_elements"]:
        texts[el["element_id"]] = {"payload": el.get("text", "")}  # last repeated wins
    layers = dict(texts)
    image_ids, collisions = [], []
    for img in item["image"]["image_prompts"]:
        if not img.get("image_url"):
            continue
        if img["element_id"] in texts:
            collisions.append(img["element_id"])
            continue
        layers[img["element_id"]] = {"image_encoded": img["image_url"]}
        image_ids.append({"image_id": img["image_id"], "image_name": img["element_id"]})
    return layers, image_ids, collisions


def _run_build(content: list[dict[str, Any]]) -> tuple[dict[str, Any], LogCapture]:
    with network_guard(), LogCapture() as logs:
        result = build_abyssale_payload(content, "ignored-template", FORMAT_RATIO)
    return result, logs


# ---------------------------------------------------------------------------
# Property 34 (task 36.3)
# ---------------------------------------------------------------------------


# Feature: adset-creative-diversity, Property 34: build_abyssale_payload nunca escribe una imagen sobre una capa de texto
@settings(max_examples=100, deadline=None)
@given(content=creative_contents())
def test_property_34_images_never_overwrite_text_layers(content):
    """**Validates: Requirements 15.11, 12.34, 12.35**"""
    snapshot = copy.deepcopy(content)
    result, logs = _run_build(content)

    assert result["ok"] is True
    assert content == snapshot  # input not mutated
    batch = result["payload"]["elements"]
    valid = [item for item in content if "error" not in item]
    assert len(batch) == len(valid)

    warnings = [line for line in logs.at_level("WARNING") if SKIP_WARNING in line]
    expected_warnings: list[tuple[str, str]] = []

    for item, out in zip(valid, batch):
        text_ids = {el["element_id"] for el in item["copy"]["template_elements"]}
        exp_layers, exp_image_ids, collisions = _expected_entry(item)
        template_id = item["copy"]["template_id"]

        assert out["template_id"] == template_id
        assert out["ad_channel_id"] == item["ad_channel"]["ad_id"]
        # No image layer on a text id of the same entry; text ids carry their text.
        for layer_id, layer in out["layers"].items():
            if "image_encoded" in layer:
                assert layer_id not in text_ids
        for tid in text_ids:
            assert out["layers"][tid] == exp_layers[tid]
            assert set(out["layers"][tid]) == {"payload"}
        # Colliding ids never reach image_ids; non-colliding images written as today.
        assert not {i["image_name"] for i in out["image_ids"]} & text_ids
        assert out["layers"] == exp_layers
        assert out["image_ids"] == exp_image_ids
        expected_warnings += [(template_id, eid) for eid in collisions]

    # One warning per collision, with template_id and element_id (Req 15.11).
    assert len(warnings) == len(expected_warnings)
    for line, (template_id, eid) in zip(warnings, expected_warnings):
        assert f"template_id={template_id}" in line
        assert f"element_id={eid!r}" in line
    # Image URLs never logged (Req 15.13).
    assert "X-Amz-Signature" not in logs.text
    assert "https://cdn.example" not in logs.text


# ---------------------------------------------------------------------------
# Template_Definition resolution in the Diversity_Path (task 41.1; Req 15.1, 15.3,
# 15.13, 12.33)
# ---------------------------------------------------------------------------

ID_ADSET = 173
PROJECT_ID = "test-project-id"
FAILING_AD, OTHER_AD = 11, 22  # ascending ids → Ad_Slots 0 and 1
SIGNED_URL = "https://bucket.s3.amazonaws.com/t.json?X-Amz-Signature=SECRETSIG41"
ERROR_MARKER = "SINERGIA_ERROR_MARKER_41"
CONCEPT = [{"index": 0, "concept": "A conforming concept"}]
APPROVED = {"overall_pass": True, "subset_to_regenerate": []}


def _slots_from_message(message):
    line = message.split("Variant_Slots: ", 1)[1].split("\n", 1)[0]
    return json.loads(line)


def _conforming_copies(call):
    return [
        {
            "plan_id": s["variant_key"].rsplit("_v", 1)[0],
            "variant_key": s["variant_key"],
            "template_id": s["template_id"],
            "headline": [f"Zqx headline {s['variant_key']}"],
            "primary_text": [f"Zqx body {s['variant_key']}"],
            "description": ["Zqx"],
            "cta": ["LEARN_MORE"],
            "template_elements": [{"element_id": "title", "text": f"Zqx {s['variant_key']}"}],
        }
        for s in _slots_from_message(call.message)
    ]


def _conforming_prompts(call):
    image_elements = image_elements_from_message(call.message)
    assert image_elements is not None, "Image_Prompter message has no Image_Elements line"
    return conformant_image_prompts(_slots_from_message(call.message), image_elements["elements"])


def _agents():
    return FakeRunAgent(defaults={
        ESTRATEGA_ADSET: CONCEPT,
        COPYWRITER: _conforming_copies,
        IMAGE_PROMPTER: _conforming_prompts,
        VALIDADOR_ADSET: APPROVED,
    })


def _phase1(task_id, n_variants=2):
    return asyncio.run(jrs._run_phase1(None, task_id, ID_ADSET, n_variants, PROJECT_ID))


class _TemplateDefinitionsFailingFor(FakeGetATemplateDefinition):
    """`get_a_template_definition` whose answer for `template_id` is `outcome`
    (raised if it is an exception); every other template keeps the default. Keyed by
    `template_id` so it does not depend on the order of concurrent Ads."""

    def __init__(self, template_id: str, outcome: Any) -> None:
        super().__init__()
        self.failing_template = str(template_id)
        self.outcome = outcome

    def default(self, *args: Any, **kwargs: Any) -> Any:
        if str(self._bind(args, kwargs).get("template_id")) == self.failing_template:
            if isinstance(self.outcome, BaseException):
                raise self.outcome
            return copy.deepcopy(self.outcome)
        return super().default(*args, **kwargs)


def _mock_template(template_id: str) -> dict[str, Any]:
    (template,) = [t for t in mock_templates()["templates"] if str(t["id"]) == template_id]
    return template


def _failure_outcome(case: str, template_id: str) -> Any:
    template = _mock_template(template_id)
    without_elements = {k: v for k, v in template.items() if k != "elements"}
    return {
        "exception": RuntimeError(f"fetch failed for {SIGNED_URL}"),
        "ok_false": {"ok": False, "error": ERROR_MARKER},
        "not_dict": [template],
        "dict_without_ok": {"template": template, "error": ERROR_MARKER},
        "template_missing": {"ok": True, "error": ERROR_MARKER},
        "template_none": {"ok": True, "template": None},
        "template_without_elements": {"ok": True, "template": without_elements},
    }[case]


_EXPECTED_CAUSE = {
    "exception": "get_a_template_definition raised RuntimeError",
    "ok_false": "ok == False",
    "not_dict": "ok == False",
    "dict_without_ok": "ok == False",
    "template_missing": "empty template definition",
    "template_none": "empty template definition",
    "template_without_elements": "empty template definition",
}


def _image_prompter_calls_for(run_agent, ad_id):
    return [m for m in run_agent.messages_for(IMAGE_PROMPTER) if f"plan_ad_{ad_id}_v" in m]


@pytest.mark.parametrize("use_mock_sinergia", [True, False], ids=["mock", "real"])
@pytest.mark.parametrize("case", list(_EXPECTED_CAUSE))
def test_template_definition_failure_fails_only_that_ad(case, use_mock_sinergia):
    """Req 15.3, 15.13, 12.33: the Ad whose Ad_Template cannot be resolved fails with
    `template_id` and `ad_id` (never `str(exc)` nor `error`), gets no Image_Prompter /
    Image_Generator call nor `image_prompts` Checkpoint; the other Ad continues."""
    task_id = f"t-tdef-{case}-{int(use_mock_sinergia)}"
    order = expected_template_order(task_id)
    failing_template, other_template = order[0], order[1]  # Ad_Slots 0 and 1
    definitions = _TemplateDefinitionsFailingFor(
        failing_template, _failure_outcome(case, failing_template)
    )
    run_agent = _agents()
    with patched_diversity_pipeline(
        ad_ids=[OTHER_AD, FAILING_AD], run_agent=run_agent,
        get_a_template_definition=definitions, use_mock_sinergia=use_mock_sinergia,
    ) as env:
        result = _phase1(task_id)

    reports = {r["ad_id"]: r for r in result["diversity_reports"]}
    failed = reports[FAILING_AD]
    assert failed["ad_failed"] is True
    assert f"template_id={failing_template}" in failed["error"]
    assert f"ad_id={FAILING_AD}" in failed["error"]
    assert _EXPECTED_CAUSE[case] in failed["error"]
    for secret in (SIGNED_URL, "X-Amz-Signature", ERROR_MARKER, "fetch failed"):
        assert secret not in failed["error"]
        assert secret not in env.logs.text

    # Nothing after STEP 2b for the failing Ad.
    assert _image_prompter_calls_for(run_agent, FAILING_AD) == []
    assert FAILING_AD not in [c.arguments.get("ad_id") for c in env.generate_images.calls]
    assert env.checkpoint(task_id, FAILING_AD, "image_prompts") is None
    assert not [k for k in env.redis.written_keys
                if k == cp_key(task_id, FAILING_AD, "image_prompts")]
    assert FAILING_AD not in env.save_ads.ad_ids

    # The other Ad continues to the end.
    other = reports[OTHER_AD]
    assert other["ad_failed"] is False
    assert _image_prompter_calls_for(run_agent, OTHER_AD)
    assert env.checkpoint(task_id, OTHER_AD, "image_prompts")
    assert [c.arguments.get("ad_id") for c in env.generate_images.calls] == [OTHER_AD]
    assert env.save_ads.ad_ids == [OTHER_AD]

    # One lookup per distinct template_id (the other Ad's save_ads reuses the cache).
    looked_up = [c.arguments["template_id"] for c in definitions.calls]
    assert sorted(looked_up) == sorted([failing_template, other_template])


def test_two_ads_sharing_template_resolve_definition_once():
    """Req 15.1, 12.33: N = 2 Ads with the same Ad_Template (one-template
    Template_Order) → a single `get_a_template_definition` call in the job, counting
    the lookups of `save_ads`."""
    task_id = "t-tdef-shared"
    template = mock_templates()["templates"][0]
    template_id = str(template["id"])
    definitions = FakeGetATemplateDefinition()
    with patched_diversity_pipeline(
        ad_ids=[OTHER_AD, FAILING_AD], run_agent=_agents(),
        get_template_context=FakeGetTemplateContext([template]),
        get_a_template_definition=definitions,
    ) as env:
        result = _phase1(task_id)

    assert expected_template_order(task_id, [template_id]) == [template_id]
    assert all(r["ad_failed"] is False for r in result["diversity_reports"])
    assert sorted(env.save_ads.ad_ids) == sorted([OTHER_AD, FAILING_AD])
    for ad_id in (OTHER_AD, FAILING_AD):
        plan = env.checkpoint(task_id, ad_id, "strategy")
        assert {v["template_id"] for v in plan["variants"]} == {template_id}
    assert [c.arguments["template_id"] for c in definitions.calls] == [template_id]


# --- Mock adapter and job cache (D24) ----------------------------------------


def test_adapter_wraps_mock_template_without_ok():
    template = _mock_template(mock_template_ids()[0])
    snapshot = copy.deepcopy(template)
    assert jrs._as_template_definition_response(template) == {"ok": True, "template": template}
    assert template == snapshot


@pytest.mark.parametrize("raw", [{}, None, [], "x", {"template": {"elements": []}},
                                 {"elements": "not-a-list"}])
def test_adapter_non_definitions_become_failure(raw):
    assert jrs._as_template_definition_response(raw) == {"ok": False}


@pytest.mark.parametrize("raw", [{"ok": False, "error": ERROR_MARKER},
                                 {"ok": True, "template": {"elements": []}}])
def test_adapter_passes_dicts_with_ok_unchanged(raw):
    assert jrs._as_template_definition_response(raw) is raw


def _cache_for(outcome: Any) -> tuple[Any, list[str]]:
    calls: list[str] = []

    async def fetch(template_id: str) -> Any:
        calls.append(template_id)
        if isinstance(outcome, BaseException):
            raise outcome
        return copy.deepcopy(outcome)

    return jrs._JobTemplateDefinitions(fetch, ["gradient"]), calls


@pytest.mark.parametrize("outcome", [
    {"ok": False, "error": ERROR_MARKER},
    RuntimeError(SIGNED_URL),
    {"ok": True, "template": None},
])
def test_tool_response_failure_has_no_error(outcome):
    cache, calls = _cache_for(outcome)

    async def run():
        return await cache.tool_response("tpl"), await cache.image_elements("tpl")

    response, elements = asyncio.run(run())
    assert response == {"ok": False}
    assert isinstance(elements, jrs._TemplateDefinitionFailure)
    assert SIGNED_URL not in elements.cause and ERROR_MARKER not in elements.cause
    assert calls == ["tpl"]


def test_tool_response_success_reuses_cache_and_copies_template():
    template = {"id": "tpl", "elements": [{"name": "image_0", "type": "image"},
                                         {"name": "gradient_top", "type": "image"},
                                         {"name": "hook", "type": "text"}]}
    cache, calls = _cache_for({"ok": True, "template": template})

    async def run():
        elements = await cache.image_elements("tpl")
        first = await cache.tool_response("tpl")
        first["template"]["elements"].clear()  # caller mutation must not leak
        return elements, await cache.tool_response("tpl")

    elements, second = asyncio.run(run())
    assert list(elements.element_ids) == ["image_0"]
    assert second == {"ok": True, "template": template}
    assert calls == ["tpl"]
    assert cache.calls == {"tpl": 1}


# ---------------------------------------------------------------------------
# image_prompts Checkpoint and regeneration under the Image_Elements_Checker
# (task 41.2; Req 15.6, 15.8, 15.9, 12.31, 12.32)
# ---------------------------------------------------------------------------

CP_AD = OTHER_AD


def _hook_prompts(items):
    """`items` (Image_Prompter items) with every `image_prompts` replaced by `hook` and
    `tagline` as images: the shape of Ad 102 of job `69d025e1` (Req 12.31)."""
    bad = copy.deepcopy(items)
    for item in bad:
        item["image_prompts"] = [
            {"element_id": eid, "element_type": "image", "image_prompt": f"scene {eid}",
             "image_request": "y"}
            for eid in ("hook", "tagline")
        ]
    return bad


def _hook_prompter(call):
    return _hook_prompts(_conforming_prompts(call))


def _prompt_element_ids(items):
    return {p["element_id"] for item in items for p in item.get("image_prompts") or []}


def _first_run_checkpoints(task_id):
    """Run the pipeline once for CP_AD and return its `strategy`, `copy` and
    `image_prompts` Checkpoints plus the Ad's expected Image_Elements."""
    with patched_diversity_pipeline(ad_ids=[CP_AD], run_agent=_agents()) as env:
        result = _phase1(task_id)
    assert result["diversity_reports"][0]["ad_failed"] is False
    cps = {step: env.checkpoint(task_id, CP_AD, step)
           for step in ("strategy", "copy", "image_prompts")}
    assert all(cps.values())
    (template_id,) = {v["template_id"] for v in cps["strategy"]["variants"]}
    cps["image_elements"] = expected_image_elements(_mock_template(str(template_id)))
    return cps


def _seeded_redis(task_id, cps, image_prompts):
    redis = FakeRedis()
    redis.seed_checkpoint(task_id, CP_AD, "strategy", cps["strategy"])
    redis.seed_checkpoint(task_id, CP_AD, "copy", cps["copy"])
    redis.seed_checkpoint(task_id, CP_AD, "image_prompts", image_prompts)
    return redis


def test_checkpoint_failing_image_elements_check_is_discarded_and_regenerated():
    """Req 15.9, 12.32: a Checkpoint `image_prompts` with `hook`/`tagline` as images is
    discarded with a `[{task_id}]` warning naming `ad_id` and the error count, and the
    Image_Prompter is invoked again; the Checkpoint is rewritten conforming."""
    task_id = "t-cp-image-elements-bad"
    cps = _first_run_checkpoints(task_id)
    bad = _hook_prompts(cps["image_prompts"])
    n_errors = len(check_image_elements(bad, cps["image_elements"]))
    assert n_errors > 0
    # The bad Checkpoint passes the Variant_Slot shape check: only P15 rejects it.
    plan = cps["strategy"]
    assert check_variant_items(bad, plan["variants"], plan["id"], kind="image_prompt") == []

    run_agent = _agents()
    with patched_diversity_pipeline(
        ad_ids=[CP_AD], run_agent=run_agent, redis=_seeded_redis(task_id, cps, bad),
    ) as env:
        result = _phase1(task_id)

    expected = (
        f"[{task_id}] image_prompts checkpoint for ad={CP_AD} fails the Image_Elements "
        f"check ({n_errors} error(s)); regenerating"
    )
    assert [line for line in env.logs.at_level("WARNING") if expected in line]
    assert run_agent.count(IMAGE_PROMPTER) == 1
    assert run_agent.count(ESTRATEGA_ADSET) == 0 and run_agent.count(COPYWRITER) == 0
    assert result["diversity_reports"][0]["ad_failed"] is False
    stored = env.checkpoint(task_id, CP_AD, "image_prompts")
    assert check_image_elements(stored, cps["image_elements"]) == []
    assert not _prompt_element_ids(stored) & {"hook", "tagline"}
    assert env.save_ads.ad_ids == [CP_AD]


def test_conforming_checkpoint_is_reused_without_image_prompter():
    """Req 15.9, 12.32: a Checkpoint with zero Image_Elements_Checker errors is reused."""
    task_id = "t-cp-image-elements-ok"
    cps = _first_run_checkpoints(task_id)
    assert check_image_elements(cps["image_prompts"], cps["image_elements"]) == []

    run_agent = _agents()
    redis = _seeded_redis(task_id, cps, cps["image_prompts"])
    with patched_diversity_pipeline(ad_ids=[CP_AD], run_agent=run_agent, redis=redis) as env:
        result = _phase1(task_id)

    assert run_agent.count(IMAGE_PROMPTER) == 0
    assert not [line for line in env.logs.at_level("WARNING")
                if "fails the Image_Elements check" in line]
    assert result["diversity_reports"][0]["ad_failed"] is False
    assert cp_key(task_id, CP_AD, "image_prompts") not in redis.written_keys
    assert env.save_ads.ad_ids == [CP_AD]


def test_variant_shape_error_on_first_attempt_then_valid_answer_advances():
    """Req 15.6, 12.31: `hook`/`tagline` on the first Image_Prompter attempt →
    `ERR_VARIANT_SHAPE`, retried with the rejection reasons; the second, conforming
    answer lets the pipeline continue to the end."""
    task_id = "t-shape-retry"
    run_agent = _agents()
    run_agent.push(IMAGE_PROMPTER, _hook_prompter)
    with patched_diversity_pipeline(ad_ids=[CP_AD], run_agent=run_agent) as env:
        result = _phase1(task_id)

    assert "ERR_VARIANT_SHAPE" in jrs._RETRYABLE_AGENT_CODES
    assert run_agent.count(IMAGE_PROMPTER) == 2
    first, second = run_agent.messages_for(IMAGE_PROMPTER)
    assert "YOUR PREVIOUS ANSWER WAS REJECTED" not in first
    assert second.startswith(first) and "YOUR PREVIOUS ANSWER WAS REJECTED" in second
    assert [line for line in env.logs.at_level("WARNING")
            if f"[{task_id}] image_prompter response rejected for ad={CP_AD}" in line
            and "ERR_VARIANT_SHAPE" in line]
    assert result["diversity_reports"][0]["ad_failed"] is False
    stored = env.checkpoint(task_id, CP_AD, "image_prompts")
    assert not _prompt_element_ids(stored) & {"hook", "tagline"}
    assert env.save_ads.ad_ids == [CP_AD]
    assert [c.arguments.get("ad_id") for c in env.generate_images.calls] == [CP_AD]


# --- _regenerate_variants with invalid element_ids (Req 15.8, 7.10) --------------

REGEN_TASK, REGEN_AD = "t-regen-image-elements", 101
REGEN_PLAN = f"plan_ad_{REGEN_AD}"
REGEN_TEMPLATES = ["tA", "tB"]
REGEN_ELEMENTS = ImageElements(
    template_id="tA", element_ids=("image_0",), specs=({"element_id": "image_0"},),
    preview_url=None,
)


def _regen_copy(slot, headline=None):
    return {
        "plan_id": REGEN_PLAN, "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "headline": [headline or f"H {slot['variant_key']}"], "primary_text": ["P"],
        "description": ["D"], "cta": ["LEARN_MORE"],
        "template_elements": [{"element_id": "title", "text": "H"}],
    }


async def _no_cta_check(copies):
    return None


def _regen_setup(monkeypatch, responses):
    ctx = make_adset_context([REGEN_AD])
    run_agent = FakeRunAgent(responses)
    redis = FakeRedis()
    monkeypatch.setattr(jrs, "_run_agent", run_agent)
    monkeypatch.setattr(jrs, "_redis", lambda: redis)
    factories = FakeAgentFactories()
    deps = jrs._DiversityDeps(
        get_template_context=None, delete_variants=None, validate_ctas=_no_cta_check,
        save_ads_programmatically=None, generate_images=None, build_abyssale_payload=None,
        post_to_abyssale_and_wait=None, make_estratega_adset_agent=None,
        make_copywriter_agent=factories[COPYWRITER],
        make_image_prompter_agent=factories[IMAGE_PROMPTER],
        make_validador_adset_agent=factories[VALIDADOR_ADSET], progress=lambda *_: None,
        template_definitions=jrs._JobTemplateDefinitions(
            FakeGetATemplateDefinition(), DEFAULT_DECORATIVE_IMAGE_PATTERNS),
    )
    job = jrs._DiversityJob(
        task=None, task_id=REGEN_TASK, id_adset=ID_ADSET, n_variants=2,
        project_id=PROJECT_ID, id_ad=None, custom_prompt=None, add_variant=True,
        id_variant=None, adset_context=ctx, adset_context_json=json.dumps(ctx),
    )
    slots = build_variant_slots(REGEN_PLAN, ad_slot=0, n_variants=2,
                                project_templates=["tA"])
    ad = jrs._DiversityAdInput(ad_id=REGEN_AD, ad_slot=0, territory=None, all_territories=(),
                               forbidden=("sibling anchor",),
                               templates=jrs._JobTemplates(("tA",), ("tA",)))
    plan = {"id": REGEN_PLAN, "concept": "c", "variants": [dict(s) for s in slots]}
    return deps, job, ad, plan, slots, run_agent, redis


def test_regeneration_with_invalid_element_ids_is_req_7_10_failure(monkeypatch):
    """Req 15.8, 7.10, 12.32: the regenerated image prompts of the subset use `hook` /
    `tagline` → `AgentValidationError` (`ERR_VARIANT_SHAPE`, a single attempt), treated
    as the Req 7.10 failure: previous copies and image prompts kept, no Checkpoint."""
    slots = build_variant_slots(REGEN_PLAN, ad_slot=0, n_variants=2, project_templates=["tA"])
    v2 = slots[1]["variant_key"]
    deps, job, ad, plan, slots, run_agent, redis = _regen_setup(monkeypatch, {
        VALIDADOR_ADSET: [{"overall_pass": False, "subset_to_regenerate": [v2]},
                          {"overall_pass": True, "subset_to_regenerate": []}],
        COPYWRITER: [[_regen_copy(slots[1], headline="new headline")]],
        IMAGE_PROMPTER: [_hook_prompts(conformant_image_prompts([slots[1]], ["image_0"]))],
    })
    copies0 = [_regen_copy(s) for s in slots]
    prompts0 = conformant_image_prompts(slots, REGEN_ELEMENTS.element_ids)
    snapshot = copy.deepcopy((copies0, prompts0))

    with LogCapture() as logs:
        copies, prompts, report, _ = asyncio.run(jrs._diversity_validation_loop(
            deps, ad, job, plan, copies0, prompts0, project_templates=["tA"],
            image_elements=REGEN_ELEMENTS,
        ))

    # Image_Elements forwarded to the regeneration; one attempt only (no retry).
    assert run_agent.count(IMAGE_PROMPTER) == 1
    (message,) = run_agent.messages_for(IMAGE_PROMPTER)
    assert image_elements_from_message(message)["elements"][0]["element_id"] == "image_0"
    # Req 7.10 — previous state kept, no Checkpoint written, loop continues.
    assert (copies, prompts) == snapshot
    assert jrs._cp_key(REGEN_TASK, REGEN_AD, "image_prompts") not in redis.data
    assert jrs._cp_key(REGEN_TASK, REGEN_AD, "copy") not in redis.data
    assert [line for line in logs.at_level("WARNING")
            if f"[{REGEN_TASK}] regeneration failed for ad={REGEN_AD}" in line]
    assert report["overall_pass"] is True and report["iterations"] == 2
    assert not _prompt_element_ids(prompts) & {"hook", "tagline"}


def test_generate_variant_prompts_rejects_invalid_element_ids_with_variant_shape(monkeypatch):
    """Req 15.6, 15.8: the composite validator turns `hook`/`tagline` into an
    `AgentValidationError` with `ERR_VARIANT_SHAPE` naming the variant_key, expected
    and received ids."""
    slots = build_variant_slots(REGEN_PLAN, ad_slot=0, n_variants=1, project_templates=["tA"])
    deps, job, ad, plan, _, run_agent, _ = _regen_setup(monkeypatch, {
        IMAGE_PROMPTER: [_hook_prompts(conformant_image_prompts(slots, ["image_0"]))],
    })
    with pytest.raises(AgentValidationError) as exc:
        asyncio.run(jrs._generate_variant_prompts(
            deps, ad, job, plan, slots, [_regen_copy(slots[0])], user_id="u",
            image_elements=REGEN_ELEMENTS,
        ))
    assert exc.value.code == "ERR_VARIANT_SHAPE"
    errors = " ".join(exc.value.errors)
    assert slots[0]["variant_key"] in errors
    assert all(eid in errors for eid in ("image_0", "hook", "tagline"))
    assert run_agent.count(IMAGE_PROMPTER) == 1


# ---------------------------------------------------------------------------
# Defence in depth: _finish_diversity_ad filtering before the Image_Generator and
# build_abyssale_payload text-layer protection (task 41.3; Req 15.10, 15.11, 12.34)
# ---------------------------------------------------------------------------

FIN_TASK, FIN_AD = "t-finish-image-elements", 101
FIN_PLAN = f"plan_ad_{FIN_AD}"
FIN_ELEMENTS = ImageElements(
    template_id="tA", element_ids=("image_0",), specs=({"element_id": "image_0"},),
    preview_url=None,
)


def _fin_prompt(slot, element_ids):
    return {
        "plan_id": FIN_PLAN, "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "image_prompts": [{"element_id": eid, "element_type": "image",
                           "image_prompt": f"scene {eid}", "image_request": "r"}
                          for eid in element_ids],
    }


def _finish_with(monkeypatch, element_ids_per_variant):
    """Run `_finish_diversity_ad` with one Variant_Slot per entry of
    `element_ids_per_variant` (the `element_id`s of its image prompts) and the
    Image_Elements `("image_0",)`. Returns (result, slots, generate_images calls,
    save_ads calls, prompts passed in, logs)."""
    redis = FakeRedis()
    monkeypatch.setattr(jrs, "_redis", lambda: redis)
    return _run_finish(
        [_fin_prompt(s, ids) for s, ids in zip(
            build_variant_slots(FIN_PLAN, ad_slot=0, n_variants=len(element_ids_per_variant),
                                project_templates=["tA"]),
            element_ids_per_variant)],
        FIN_ELEMENTS,
    )


def _run_finish(prompts, image_elements):
    """Core of `_finish_with`: `prompts` (one Image_Prompter item per Variant_Slot, any
    `image_prompts` elements) through `_finish_diversity_ad` with fresh fakes. The
    caller is responsible for `jrs._redis`."""
    n = len(prompts)
    slots = build_variant_slots(FIN_PLAN, ad_slot=0, n_variants=n, project_templates=["tA"])
    generate_calls: list[list[dict]] = []
    save_calls: list[list[str]] = []

    async def generate_images(prompts, ad_id):
        generate_calls.append(copy.deepcopy(prompts))
        return {"ok": True, "generated_images": [
            {**p, "image_prompts": [{**e, "image_url": "data:x", "image_id": "IMG"}
                                    for e in p["image_prompts"]]}
            for p in prompts
        ]}

    async def save_ads_programmatically(id_adset, ad_id, copies):
        save_calls.append([c["variant_key"] for c in copies])
        return [{"plan_id": c["plan_id"], "template_id": c["template_id"],
                 "variant_key": c["variant_key"], "saved": True, "ad_id": 900 + i}
                for i, c in enumerate(copies)]

    async def post_to_abyssale_and_wait(task_id, payload, id_adset, ad_id):
        return {"ok": True, "batch_id": ["b1"]}

    deps = jrs._DiversityDeps(
        get_template_context=None, delete_variants=None, validate_ctas=None,
        save_ads_programmatically=save_ads_programmatically, generate_images=generate_images,
        build_abyssale_payload=build_abyssale_payload,
        post_to_abyssale_and_wait=post_to_abyssale_and_wait,
        make_estratega_adset_agent=None, make_copywriter_agent=None,
        make_image_prompter_agent=None, make_validador_adset_agent=None,
        progress=lambda *_: None,
        template_definitions=jrs._JobTemplateDefinitions(
            FakeGetATemplateDefinition(), DEFAULT_DECORATIVE_IMAGE_PATTERNS),
    )
    job = jrs._DiversityJob(
        task=None, task_id=FIN_TASK, id_adset=ID_ADSET, n_variants=n,
        project_id=PROJECT_ID, id_ad=None, custom_prompt=None, add_variant=True,
        id_variant=None, adset_context={}, adset_context_json="{}",
    )
    ad = jrs._DiversityAdInput(ad_id=FIN_AD, ad_slot=0, territory=None, all_territories=(),
                               forbidden=(), templates=jrs._JobTemplates(("tA",), ("tA",)))
    plan = {"id": FIN_PLAN, "concept": "c", "variants": [dict(s) for s in slots]}
    copies = [_regen_copy({**s}) for s in slots]
    for c in copies:
        c["plan_id"] = FIN_PLAN
    snapshot = copy.deepcopy(prompts)
    report = {"ad_id": FIN_AD, "plan_id": FIN_PLAN, "deterministic_pass": True,
              "deterministic_errors": [], "deterministic_warnings": [], "overall_pass": True,
              "iterations": 1, "subset_to_regenerate": [], "ad_failed": False, "error": None}
    verdict = {"overall_pass": True, "subset_to_regenerate": []}
    with network_guard(), LogCapture() as logs:
        result = asyncio.run(jrs._finish_diversity_ad(
            deps, ad, job, plan, copies, prompts, report, verdict,
            image_elements=image_elements,
        ))
    assert prompts == snapshot  # caller's prompts not mutated
    return result, slots, generate_calls, save_calls, snapshot, logs


def _dropped_warnings(logs):
    return [line for line in logs.at_level("WARNING")
            if f"[{FIN_TASK}] image prompt dropped ad={FIN_AD}" in line]


def _proposal_element_ids(result):
    """element_ids of the image prompts carried by the proposals, per variant_key."""
    return {p["variant_key"]: [e.get("element_id") for e in p["image_prompts"]]
            for p in result.proposals}


def test_finish_drops_foreign_prompt_with_warning(monkeypatch):
    """Req 15.10, 12.34: a prompt whose element_id is not an Image_Element (`hook`)
    never reaches the Image_Generator and is logged with task_id, ad_id, variant_key
    and element_id; proposals keep the unfiltered prompts."""
    result, slots, gen_calls, save_calls, prompts, logs = _finish_with(
        monkeypatch, [["image_0", "hook"], ["image_0"]])
    v1, v2 = (s["variant_key"] for s in slots)

    (sent,) = gen_calls
    assert [p["variant_key"] for p in sent] == [v1, v2]
    assert _prompt_element_ids(sent) == {"image_0"}
    assert [[e["element_id"] for e in p["image_prompts"]] for p in sent] == [["image_0"]] * 2
    (warning,) = _dropped_warnings(logs)
    assert f"variant_key={v1}" in warning and "element_id=hook" in warning
    assert save_calls == [[v1, v2]]
    # Proposals keep the unfiltered prompts (D27).
    assert _proposal_element_ids(result) == {v1: ["image_0", "hook"], v2: ["image_0"]}


def test_finish_excludes_variant_left_without_elements(monkeypatch):
    """Req 15.10, 12.34: a variant whose prompts are all foreign is not sent."""
    result, slots, gen_calls, save_calls, _, logs = _finish_with(
        monkeypatch, [["hook", "tagline"], ["image_0"]])
    v1, v2 = (s["variant_key"] for s in slots)

    (sent,) = gen_calls
    assert [p["variant_key"] for p in sent] == [v2]
    assert _prompt_element_ids(sent) == {"image_0"}
    warnings = _dropped_warnings(logs)
    assert len(warnings) == 2
    assert all(f"variant_key={v1}" in w for w in warnings)
    assert {"element_id=hook", "element_id=tagline"} == {
        w[w.index("element_id="):].split()[0] for w in warnings}
    assert save_calls == [[v1, v2]]  # the pipeline continues for every variant


def test_finish_skips_image_generator_when_no_prompt_remains(monkeypatch):
    """Req 15.10, 12.34: no Image_Element prompt left → generate_images not invoked;
    save_ads and Abyssale still run for every variant."""
    result, slots, gen_calls, save_calls, _, logs = _finish_with(
        monkeypatch, [["hook"], ["tagline"]])
    keys = [s["variant_key"] for s in slots]

    assert gen_calls == []
    assert len(_dropped_warnings(logs)) == 2
    assert save_calls == [keys]
    assert [p["variant_key"] for p in result.proposals] == keys
    assert result.abyssale_batch_id == ["b1"]


@pytest.mark.parametrize("diversity_flag", [True, False], ids=["flag_on", "flag_off"])
def test_build_abyssale_payload_keeps_hook_text_layer(monkeypatch, diversity_flag):
    """Req 15.11, 12.34: `hook` as text plus `hook` as image with `image_url` →
    `layers["hook"] == {"payload": <text>}`, no `hook` in `image_ids`, one warning;
    identical with the Diversity_Flag off (shared by both paths)."""
    import agents.tools.abyssale_tools as abyssale_tools

    monkeypatch.setattr(abyssale_tools.settings, "USE_ADSET_CREATIVE_DIVERSITY",
                        diversity_flag, raising=False)
    entry = {
        "plan": {"id": "plan-1"},
        "copy": {"template_id": "1bb5c1ad",
                 "template_elements": [{"element_id": "hook", "text": "Hook text"},
                                       {"element_id": "tagline", "text": "Tag"}]},
        "image": {"image_prompts": [
            {"element_id": "hook", "image_id": "IMG-H",
             "image_url": "https://cdn.example/h.png?X-Amz-Signature=sigH"},
            {"element_id": "image_0", "image_id": "IMG-0",
             "image_url": "https://cdn.example/0.png?X-Amz-Signature=sig0"},
        ]},
        "ad_channel": {"ad_id": 900},
    }
    result, logs = _run_build([entry])

    (out,) = result["payload"]["elements"]
    assert out["layers"]["hook"] == {"payload": "Hook text"}
    assert out["layers"]["tagline"] == {"payload": "Tag"}
    assert out["layers"]["image_0"] == {
        "image_encoded": "https://cdn.example/0.png?X-Amz-Signature=sig0"}
    assert out["image_ids"] == [{"image_id": "IMG-0", "image_name": "image_0"}]
    (warning,) = [line for line in logs.at_level("WARNING") if SKIP_WARNING in line]
    assert "template_id=1bb5c1ad" in warning and "element_id='hook'" in warning
    assert "X-Amz-Signature" not in logs.text


# ---------------------------------------------------------------------------
# Property 33 (task 41.4): only Image_Elements reach the Image_Generator
# ---------------------------------------------------------------------------

# Small pool so Image_Elements and prompt element_ids collide often; includes text ids
# and near misses ("" and a trailing space) that must not pass exact equality.
_P33_IDS = ["image_0", "image_1", "product_image", "hook", "tagline", "", "image_0 "]
_P33_NON_DICTS = st.one_of(st.none(), st.integers(-5, 5), st.sampled_from(["image_0", "hook"]),
                           st.just(["image_0"]), st.booleans())


@st.composite
def _p33_element(draw):
    kind = draw(st.sampled_from(["id", "id", "id", "no_id", "non_str_id", "non_dict"]))
    if kind == "non_dict":
        return draw(_P33_NON_DICTS)
    element: dict[str, Any] = {"element_type": "image", "image_prompt": "scene",
                               "image_request": "r"}
    if kind == "id":
        element["element_id"] = draw(st.sampled_from(_P33_IDS))
    elif kind == "non_str_id":
        element["element_id"] = draw(st.one_of(st.none(), st.integers(0, 3),
                                               st.just(["image_0"])))
    return element


@st.composite
def _p33_case(draw):
    element_ids = tuple(draw(st.lists(st.sampled_from(_P33_IDS[:5]), max_size=3,
                                      unique=True)))
    image_elements = ImageElements(
        template_id="tA", element_ids=element_ids,
        specs=tuple({"element_id": eid} for eid in element_ids), preview_url=None,
    )
    n = draw(st.integers(1, 3))
    slots = build_variant_slots(FIN_PLAN, ad_slot=0, n_variants=n, project_templates=["tA"])
    prompts = []
    for slot in slots:
        item = _fin_prompt(slot, [])
        # Repeats come from the small id pool (lists may hold the same id twice).
        item["image_prompts"] = draw(st.lists(_p33_element(), max_size=5))
        prompts.append(item)
    return image_elements, prompts


def _p33_label(element):
    """Expected `element_id=` label of a dropped element (D25): raw `str`, `<type>`
    otherwise, a non-dict element shown by its own type."""
    if not isinstance(element, dict):
        return f"<{type(element).__name__}>"
    element_id = element.get("element_id")
    return element_id if isinstance(element_id, str) else f"<{type(element_id).__name__}>"


# Feature: adset-creative-diversity, Property 33: Solo Image_Elements llegan al Image_Generator
@settings(max_examples=100, deadline=None)
@given(case=_p33_case())
def test_property_33_only_image_elements_reach_image_generator(case):
    """**Validates: Requirements 15.10, 12.34**"""
    image_elements, prompts = case
    allowed = set(image_elements.element_ids)
    snapshot = copy.deepcopy(prompts)

    # Independent oracle: kept elements per variant and dropped (variant_key, label).
    expected_sent, expected_dropped = [], []
    for item in prompts:
        kept = []
        for element in item["image_prompts"]:
            if (isinstance(element, dict) and isinstance(element.get("element_id"), str)
                    and element["element_id"] in allowed):
                kept.append(element)
            else:
                expected_dropped.append((item["variant_key"], _p33_label(element)))
        if kept:
            expected_sent.append((item["variant_key"], kept))

    # Fresh Redis per example, patched and restored manually (no pytest fixture).
    redis = FakeRedis()
    original_redis = jrs._redis
    jrs._redis = lambda: redis
    try:
        result, _, gen_calls, save_calls, passed, logs = _run_finish(prompts, image_elements)
    finally:
        jrs._redis = original_redis

    # Input not mutated (also asserted inside _run_finish).
    assert prompts == snapshot and passed == snapshot

    if not expected_sent:
        assert gen_calls == []  # nothing left → generator not invoked
    else:
        (sent,) = gen_calls
        for variant in sent:
            assert variant["image_prompts"], "variant sent without elements"
            for element in variant["image_prompts"]:
                assert isinstance(element, dict)
                assert element["element_id"] in allowed
        assert [(v["variant_key"], v["image_prompts"]) for v in sent] == expected_sent

    # Exactly one warning per dropped element, with task_id, ad_id, variant_key, element_id.
    assert _dropped_warnings(logs) == [
        f"[{FIN_TASK}] image prompt dropped ad={FIN_AD} variant_key={vk} element_id={label}"
        for vk, label in expected_dropped
    ]
    # The rest of the Ad continues for every variant; proposals keep unfiltered prompts.
    assert save_calls == [[item["variant_key"] for item in prompts]]
    assert [p["image_prompts"] for p in result.proposals] == [
        item["image_prompts"] for item in snapshot]


# ---------------------------------------------------------------------------
# Property 35 (task 41.5): one resolution per template_id, failure isolated per Ad
# ---------------------------------------------------------------------------

P35_AD_IDS = [11, 22, 33, 44]  # ascending → Ad_Slots 0..3; no id is a prefix of another
_P35_VALID = ("valid", "valid_without_image_elements", "valid_empty_elements")
_P35_CASES = _P35_VALID + tuple(_EXPECTED_CAUSE)
P35_API_KEY = "SECRETKEY41"
_P35_SECRETS = (SIGNED_URL, "X-Amz-Signature", "SECRETSIG41", P35_API_KEY, ERROR_MARKER,
                "fetch failed")


class _TemplateDefinitionsByOutcome(FakeGetATemplateDefinition):
    """`get_a_template_definition` answering `outcomes[template_id]` (raised if it is an
    exception). Keyed by `template_id`, so independent of the order of concurrent Ads."""

    def __init__(self, outcomes: dict[str, Any]) -> None:
        super().__init__()
        self.outcomes = {str(k): v for k, v in outcomes.items()}

    def default(self, *args: Any, **kwargs: Any) -> Any:
        outcome = self.outcomes[str(self._bind(args, kwargs).get("template_id"))]
        if isinstance(outcome, BaseException):
            raise outcome
        return copy.deepcopy(outcome)


def _p35_outcome(case: str, template_id: str) -> tuple[Any, list[str] | None]:
    """(answer of `get_a_template_definition`, expected Image_Elements or None if the
    Ad_Template must fail)."""
    if case == "exception":  # signed URL plus a key in the message
        return RuntimeError(f"fetch failed for {SIGNED_URL} x-api-key={P35_API_KEY}"), None
    if case not in _P35_VALID:
        return _failure_outcome(case, template_id), None
    template = _mock_template(template_id)
    if case == "valid_without_image_elements":
        template["elements"] = [e for e in template["elements"] if e.get("type") != "image"]
    elif case == "valid_empty_elements":
        template["elements"] = []
    return {"ok": True, "template": template}, expected_image_elements(template)


@st.composite
def _p35_scenario(draw):
    n_ads = draw(st.integers(1, 4))
    task_id = f"t-p35-{draw(st.integers(0, 10_000))}"
    order = expected_template_order(task_id)
    cases = {tid: draw(st.sampled_from(_P35_CASES)) for tid in mock_template_ids()}
    return {
        "n_ads": n_ads, "task_id": task_id, "order": order, "cases": cases,
        "n_variants": draw(st.integers(1, 2)),
        "use_mock_sinergia": draw(st.booleans()),
        "ad_ids": draw(st.permutations(P35_AD_IDS[:n_ads])),  # input order is arbitrary
    }


# Feature: adset-creative-diversity, Property 35: Una resolución por template_id y fallo aislado por Ad
@settings(max_examples=100, deadline=None)
@given(scenario=_p35_scenario())
def test_property_35_one_resolution_per_template_and_isolated_ad_failure(scenario):
    """**Validates: Requirements 15.1, 15.3, 15.13, 12.33**"""
    task_id, order, cases = scenario["task_id"], scenario["order"], scenario["cases"]
    outcomes, expected_elements = {}, {}
    for tid, case in cases.items():
        outcomes[tid], expected_elements[tid] = _p35_outcome(case, tid)
    ads = sorted(scenario["ad_ids"])
    # Independent oracle: Ad_Slot k uses Template_Order[k mod len] (Req 12.2, 12.20).
    template_of = {ad_id: order[slot % len(order)] for slot, ad_id in enumerate(ads)}
    failing = [a for a in ads if expected_elements[template_of[a]] is None]
    valid = [a for a in ads if a not in failing]

    # Fresh fakes per example.
    definitions = _TemplateDefinitionsByOutcome(outcomes)
    run_agent = _agents()
    with patched_diversity_pipeline(
        ad_ids=scenario["ad_ids"], run_agent=run_agent,
        get_a_template_definition=definitions,
        use_mock_sinergia=scenario["use_mock_sinergia"],
    ) as env:
        result = _phase1(task_id, n_variants=scenario["n_variants"])

    reports = {r["ad_id"]: r for r in result["diversity_reports"]}
    assert sorted(reports) == ads

    # One lookup per distinct template_id of the processed Ads, save_ads included.
    looked_up = [str(c.arguments["template_id"]) for c in definitions.calls]
    assert sorted(looked_up) == sorted({template_of[a] for a in ads})

    for ad_id in ads:
        plan = env.checkpoint(task_id, ad_id, "strategy")
        assert {str(v["template_id"]) for v in plan["variants"]} == {template_of[ad_id]}

    generated_for = [c.arguments.get("ad_id") for c in env.generate_images.calls]
    for ad_id in failing:
        tid = template_of[ad_id]
        report = reports[ad_id]
        assert report["ad_failed"] is True
        assert f"template_id={tid}" in report["error"]
        assert f"ad_id={ad_id}" in report["error"]
        assert _EXPECTED_CAUSE[cases[tid]] in report["error"]
        for secret in _P35_SECRETS:
            assert secret not in report["error"]
        # Nothing after STEP 2b for the failing Ad.
        assert _image_prompter_calls_for(run_agent, ad_id) == []
        assert ad_id not in generated_for
        assert env.checkpoint(task_id, ad_id, "image_prompts") is None
        assert cp_key(task_id, ad_id, "image_prompts") not in env.redis.written_keys
        assert ad_id not in env.save_ads.ad_ids

    for ad_id in valid:
        elements = expected_elements[template_of[ad_id]]
        assert reports[ad_id]["ad_failed"] is False
        stored = env.checkpoint(task_id, ad_id, "image_prompts")
        assert stored, f"no image_prompts checkpoint for ad={ad_id}"
        assert len(stored) == scenario["n_variants"]
        for item in stored:
            assert [p["element_id"] for p in item["image_prompts"]] == elements
        # The Image_Generator only runs for Ads with something to generate (Req 15.10).
        assert (ad_id in generated_for) == bool(elements)
    assert sorted(env.save_ads.ad_ids) == valid
    assert sorted(generated_for) == sorted(a for a in valid if expected_elements[template_of[a]])

    # No log line carries the signature, the key nor the `error` marker (Req 15.13).
    for secret in _P35_SECRETS:
        assert secret not in env.logs.text


# ---------------------------------------------------------------------------
# Property 36: image_prompts Checkpoint reuse and regeneration under Image_Elements
# (task 41.6; Req 15.8, 15.9, 12.32)
# ---------------------------------------------------------------------------

from hypothesis import assume  # noqa: E402

from tests.test_adset_diversity_image_elements import _variant  # noqa: E402  (Property 30)

P36_TASK = "t-p36-checkpoint"
_P36_FIRST_RUN: dict[str, Any] = {}


def _p36_first_run() -> dict[str, Any]:
    """First-run Checkpoints of CP_AD, computed once (deterministic for P36_TASK)."""
    if not _P36_FIRST_RUN:
        _P36_FIRST_RUN.update(_first_run_checkpoints(P36_TASK))
    return copy.deepcopy(_P36_FIRST_RUN)


def _p36_with_slot_identity(variant: dict, base: dict) -> dict:
    """`variant` (Property 30 generator) carrying the plan_id / variant_key /
    template_id of the Variant_Slot in `base`, so `check_variant_items` passes and
    only the Image_Elements_Checker decides. Dict prompts get the prompt fields the
    Image_Generator reads (irrelevant to the checker)."""
    item = {k: v for k, v in base.items() if k != "image_prompts"}
    if "image_prompts" in variant:
        item["image_prompts"] = variant["image_prompts"]
        if isinstance(item["image_prompts"], list):
            for p in item["image_prompts"]:
                if isinstance(p, dict):
                    p.setdefault("image_prompt", f"scene {p.get('element_id')}")
                    p.setdefault("image_request", "y")
    # Wire form: LLM answers and Redis Checkpoints are JSON, so e.g. a tuple drawn by
    # the Property 30 generator reaches the pipeline as a list.
    return json.loads(json.dumps(item))


# Feature: adset-creative-diversity, Property 36: Reutilización del Checkpoint image_prompts y regeneración con Image_Elements
@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_property_36_image_prompts_checkpoint_reuse(data):
    """**Validates: Requirements 15.8, 15.9, 12.32**"""
    cps = _p36_first_run()
    plan, expected = cps["strategy"], cps["image_elements"]
    seeded = [
        _p36_with_slot_identity(data.draw(_variant(expected), label="variant"), base)
        for base in cps["image_prompts"]
    ]
    seeded = data.draw(st.permutations(seeded), label="order")
    assert check_variant_items(seeded, plan["variants"], plan["id"], kind="image_prompt") == []
    errors = check_image_elements(seeded, expected)

    # Fresh fakes per example.
    run_agent = _agents()
    redis = _seeded_redis(P36_TASK, cps, seeded)
    with patched_diversity_pipeline(ad_ids=[CP_AD], run_agent=run_agent, redis=redis) as env:
        result = _phase1(P36_TASK)

    assert result["diversity_reports"][0]["ad_failed"] is False
    assert run_agent.count(ESTRATEGA_ADSET) == 0 and run_agent.count(COPYWRITER) == 0
    # The Validador_Adset approves at once: no regenerations, so every Image_Prompter
    # call is the Checkpoint fallback.
    assert (run_agent.count(IMAGE_PROMPTER) == 0) == (errors == [])
    discarded = [
        line for line in env.logs.at_level("WARNING")
        if f"[{P36_TASK}] image_prompts checkpoint for ad={CP_AD} fails the "
           f"Image_Elements check ({len(errors)} error(s)); regenerating" in line
    ]
    stored = env.checkpoint(P36_TASK, CP_AD, "image_prompts")
    if errors:
        assert discarded
        assert run_agent.count(IMAGE_PROMPTER) == 1
        assert check_image_elements(stored, expected) == []
        assert cp_key(P36_TASK, CP_AD, "image_prompts") in redis.written_keys
    else:
        assert not [line for line in env.logs.at_level("WARNING")
                    if "fails the Image_Elements check" in line]
        assert cp_key(P36_TASK, CP_AD, "image_prompts") not in redis.written_keys
        assert stored == seeded
    assert env.save_ads.ad_ids == [CP_AD]


# Feature: adset-creative-diversity, Property 36: Reutilización del Checkpoint image_prompts y regeneración con Image_Elements
@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_property_36_failing_regeneration_keeps_previous_prompts(data):
    """**Validates: Requirements 15.8, 15.9, 12.32**"""
    all_slots = build_variant_slots(REGEN_PLAN, ad_slot=0, n_variants=2,
                                    project_templates=["tA"])
    rounds = data.draw(st.integers(1, 2), label="failing_rounds")
    subsets = [
        data.draw(st.lists(st.sampled_from([s["variant_key"] for s in all_slots]),
                           min_size=1, max_size=2, unique=True), label=f"subset_{r}")
        for r in range(rounds)
    ]
    by_key = {s["variant_key"]: s for s in all_slots}
    prompter_answers = []
    for r, keys in enumerate(subsets):
        bases = conformant_image_prompts([by_key[k] for k in keys], REGEN_ELEMENTS.element_ids)
        answer = [
            _p36_with_slot_identity(
                data.draw(_variant(list(REGEN_ELEMENTS.element_ids)), label=f"v_{r}"), base)
            for base in bases
        ]
        assume(check_image_elements(answer, REGEN_ELEMENTS) != [])  # non-conforming
        prompter_answers.append(answer)
    responses = {
        VALIDADOR_ADSET: [{"overall_pass": False, "subset_to_regenerate": keys}
                          for keys in subsets] + [APPROVED],
        COPYWRITER: [[_regen_copy(by_key[k], headline=f"new headline {r}") for k in keys]
                     for r, keys in enumerate(subsets)],
        IMAGE_PROMPTER: prompter_answers,
    }

    # Fresh fakes per example; module attributes patched and restored manually.
    with pytest.MonkeyPatch.context() as mp:
        deps, job, ad, plan, slots, run_agent, redis = _regen_setup(mp, responses)
        copies0 = [_regen_copy(s) for s in slots]
        prompts0 = conformant_image_prompts(slots, REGEN_ELEMENTS.element_ids)
        snapshot = copy.deepcopy((copies0, prompts0))
        with LogCapture() as logs:
            copies, prompts, report, _ = asyncio.run(jrs._diversity_validation_loop(
                deps, ad, job, plan, copies0, prompts0, project_templates=["tA"],
                image_elements=REGEN_ELEMENTS,
            ))

    # One single attempt per regeneration, each with the Image_Elements line.
    assert run_agent.count(IMAGE_PROMPTER) == rounds
    for message in run_agent.messages_for(IMAGE_PROMPTER):
        assert [e["element_id"] for e in image_elements_from_message(message)["elements"]] \
            == list(REGEN_ELEMENTS.element_ids)
    # Req 7.10: previous copies and image prompts kept, no Checkpoint, loop continues.
    assert (copies, prompts) == snapshot
    assert check_image_elements(prompts, REGEN_ELEMENTS) == []
    assert jrs._cp_key(REGEN_TASK, REGEN_AD, "image_prompts") not in redis.data
    assert jrs._cp_key(REGEN_TASK, REGEN_AD, "copy") not in redis.data
    failed = [line for line in logs.at_level("WARNING")
              if f"[{REGEN_TASK}] regeneration failed for ad={REGEN_AD}" in line]
    assert len(failed) == rounds
    assert report["overall_pass"] is True and report["iterations"] == rounds + 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
