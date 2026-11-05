"""Unit tests of the full Diversity_Path pipeline (adset-creative-diversity, task 11.11).

Every test runs the real `services.job_runner_service._run_phase1` with
`USE_ADSET_CREATIVE_DIVERSITY=True` on the shared in-memory fakes
(`patched_diversity_pipeline`): no Redis, Sinergia, Abyssale, Gemini, LLM,
network or real waits.

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_pipeline.py
    PYTHONPATH=. python -m tests.test_adset_diversity_pipeline
"""
import asyncio
import json

import pytest

import services.job_runner_service as jrs
from core.exceptions import AdsetCreativeDiversityError
from core.validation import AgentValidationError
from services.territory_assignment import unwrap_adset
from tests._diversity_pipeline_fakes import (
    COPYWRITER,
    ESTRATEGA_ADSET,
    IMAGE_PROMPTER,
    VALIDADOR,
    VALIDADOR_ADSET,
    FakeDeleteVariants,
    FakeGenerateImagesFromPrompts,
    FakeGetATemplateDefinition,
    FakeGetTemplateContext,
    FakePostToAbyssaleAndWait,
    FakeRedis,
    FakeRunAgent,
    FakeSaveAds,
    FakeTask,
    conformant_image_prompts,
    cp_key,
    expected_image_elements,
    expected_slots,
    expected_template_order,
    image_elements_from_message,
    make_adset_context,
    mock_template_ids,
    mock_templates,
    patched_diversity_pipeline,
)

ID_ADSET = 173
PROJECT_ID = "test-project-id"
AD_IDS = [22, 11, 33]           # deliberately unsorted: slots follow ascending id
SORTED_AD_IDS = sorted(AD_IDS)
CONCEPT = [{"index": 0, "concept": "A conforming concept"}]
APPROVED = {"overall_pass": True, "subset_to_regenerate": []}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slots_from_message(message):
    """Variant_Slots sent to the Copywriter / Image_Prompter (`Variant_Slots: [...]`)."""
    line = message.split("Variant_Slots: ", 1)[1].split("\n", 1)[0]
    return json.loads(line)


def _plan_id_of(variant_key):
    return variant_key.rsplit("_v", 1)[0]


def _conforming_copies(call):
    """One valid, mutually different copy per requested Variant_Slot."""
    return [
        {
            "plan_id": _plan_id_of(s["variant_key"]),
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
    """P15 (Req 12.2): one entry per Image_Element of the message's `Image_Elements:`
    line, with `element_type: "image"`. A missing line fails the test (no fallback)."""
    image_elements = image_elements_from_message(call.message)
    assert image_elements is not None, "Image_Prompter message has no Image_Elements line"
    return conformant_image_prompts(_slots_from_message(call.message),
                                    image_elements["elements"])


def _agents(**overrides):
    """FakeRunAgent whose agents all return conforming, approved responses."""
    defaults = {
        ESTRATEGA_ADSET: CONCEPT,
        COPYWRITER: _conforming_copies,
        IMAGE_PROMPTER: _conforming_prompts,
        VALIDADOR_ADSET: APPROVED,
    }
    defaults.update(overrides)
    return FakeRunAgent(defaults=defaults)


def _phase1(task_id, n_variants, **kwargs):
    return asyncio.run(jrs._run_phase1(
        None, task_id, ID_ADSET, n_variants, PROJECT_ID, **kwargs,
    ))


def _territories(env, task_id):
    """Checkpoint `adset_territories` (one AdDescription dict per Ad_Slot)."""
    return env.checkpoint(task_id, ID_ADSET, "adset_territories")


def _warnings(env, *needles):
    return [r.message for r in env.logs.records
            if r.level == "WARNING" and all(n in r.message for n in needles)]


def _no_anchor_context(ad_ids):
    ctx = make_adset_context(ad_ids)
    adset = unwrap_adset(ctx)
    adset["campaign"] = {}
    adset["buyer"] = {}
    return ctx


def _assert_template_rotation(env, task_id, ad_id, ad_slot, n_variants):
    """P11/P12 (D15/D16): every variant of the Ad uses `order[ad_slot % len(order)]`,
    with `order` the Template_Order of the job `task_id`; each Variant_Slot carries its
    Variant_Angle (P14, D22; Req 14.1)."""
    order = expected_template_order(task_id)
    plan = env.checkpoint(task_id, ad_id, "strategy")
    template = order[ad_slot % len(order)]
    expected = [template] * n_variants
    assert plan["variants"] == expected_slots(f"plan_ad_{ad_id}", n_variants, template)
    copies = env.checkpoint(task_id, ad_id, "copy")
    assert [c["template_id"] for c in copies] == expected
    (payloads,) = [c.arguments["payloads"] for c in env.save_ads.calls
                   if c.arguments["id_ad"] == ad_id]
    assert [p["media_template_id"] for p in payloads] == expected
    (abyssale_payload,) = [c.arguments["abyssale_payload"] for c in env.post_to_abyssale.calls
                           if c.arguments["ad_id"] == ad_id]
    assert [e["template_id"] for e in abyssale_payload["elements"]] == expected


# ---------------------------------------------------------------------------
# Happy paths (Req 12.3, 12.4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_variants", [2, 3])
def test_scenario_1_happy_path(n_variants):
    task_id = f"t-s1-{n_variants}"
    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=run_agent) as env:
        result = _phase1(task_id, n_variants)

    territories = _territories(env, task_id)
    assert [t["ad_id"] for t in territories] == SORTED_AD_IDS
    anchors = [t["territory"]["anchor_primary"]["text"] for t in territories]
    assert len(set(anchors)) == len(anchors)

    ad_templates = []
    for ad_slot, ad_id in enumerate(SORTED_AD_IDS):
        plan = env.checkpoint(task_id, ad_id, "strategy")
        assert plan["id"] == f"plan_ad_{ad_id}"
        copies = env.checkpoint(task_id, ad_id, "copy")
        assert len(copies) == n_variants
        assert {c["plan_id"] for c in copies} == {plan["id"]}
        # P11: one Ad_Template per Ad, shared by all its variants.
        _assert_template_rotation(env, task_id, ad_id, ad_slot, n_variants)
        ad_templates.append(plan["variants"][0]["template_id"])
    # 3 Ads <= 3 mock templates: each Ad gets a distinct template.
    assert len(set(ad_templates)) == len(SORTED_AD_IDS)

    assert sorted(env.save_ads.ad_ids) == SORTED_AD_IDS
    assert env.save_ads.call_count == len(AD_IDS)
    reports = result["diversity_reports"]
    assert sorted(r["ad_id"] for r in reports) == SORTED_AD_IDS
    assert all(r["overall_pass"] and not r["ad_failed"] for r in reports)
    assert env.delete_variants.call_count == 0


def test_scenario_2_add_variant_true():
    s1_task, s2_task = "t-s2-ref", "t-s2"
    id_ad = SORTED_AD_IDS[1]
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents()) as env1:
        _phase1(s1_task, 2)
        reference = _territories(env1, s1_task)

    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=run_agent) as env:
        result = _phase1(s2_task, 2, id_ad=id_ad, add_variant=True, id_variant=[901])

    assert env.save_ads.ad_ids == [id_ad]
    assert run_agent.count(COPYWRITER) == 1
    assert [r["ad_id"] for r in result["diversity_reports"]] == [id_ad]

    territories = _territories(env, s2_task)
    slot = SORTED_AD_IDS.index(id_ad)
    assert territories[slot]["territory"] == reference[slot]["territory"]

    plan = env.checkpoint(s2_task, id_ad, "strategy")
    forbidden = plan["_territory"]["territorio_prohibido"]
    own = territories[slot]["territory"]["anchor_primary"]["text"]
    siblings = [t["territory"]["anchor_primary"]["text"]
                for i, t in enumerate(territories) if i != slot]
    assert forbidden == siblings
    assert own not in forbidden
    assert env.delete_variants.call_count == 0


def test_scenario_2_id_ad_absent_gets_extra_slot():
    task_id = "t-s2-absent"
    id_ad = 999
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents()) as env:
        result = _phase1(task_id, 2, id_ad=id_ad)

    territories = _territories(env, task_id)
    assert [t["ad_id"] for t in territories] == SORTED_AD_IDS + [id_ad]
    assert env.assign_territories.calls[0]["kwargs"]["n_ads"] == len(AD_IDS) + 1
    assert _warnings(env, f"[{task_id}]", str(id_ad))
    assert env.save_ads.ad_ids == [id_ad]
    assert [r["ad_id"] for r in result["diversity_reports"]] == [id_ad]


def test_scenario_1_adset_without_ads():
    task_id = "t-no-ads"
    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=[], run_agent=run_agent) as env:
        result = _phase1(task_id, 2)

    for key in ("proposals", "saved_ads", "abyssale_batch_ids", "diversity_reports"):
        assert result[key] == []
    assert env.assign_territories.call_count == 0
    assert run_agent.call_count == 0
    assert _warnings(env, f"[{task_id}]")


def test_adset_without_anchors_fails_job():
    task_id = "t-no-anchors"
    run_agent = _agents()
    with patched_diversity_pipeline(adset_context=_no_anchor_context(AD_IDS),
                                    run_agent=run_agent) as env:
        with pytest.raises(AdsetCreativeDiversityError) as excinfo:
            _phase1(task_id, 2)

    message = getattr(excinfo.value, "message", None) or str(excinfo.value)
    assert str(ID_ADSET) in message
    assert run_agent.count(ESTRATEGA_ADSET) == 0
    assert run_agent.count(COPYWRITER) == 0
    assert env.generate_images.call_count == 0
    assert env.save_ads.call_count == 0


# ---------------------------------------------------------------------------
# Strategy errors (Req 4.4, 4.7, 12.14)
# ---------------------------------------------------------------------------


def test_estratega_without_concept_raises_agent_validation_error():
    run_agent = _agents(**{ESTRATEGA_ADSET: [{"index": 0}]})
    with patched_diversity_pipeline(ad_ids=[11], run_agent=run_agent) as env:
        with pytest.raises(AgentValidationError):
            _phase1("t-no-concept", 2)
    assert run_agent.count(COPYWRITER) == 0
    assert env.save_ads.call_count == 0


@pytest.mark.parametrize("template_context", [
    FakeGetTemplateContext(script=[RuntimeError("boom secret")]),
    FakeGetTemplateContext(templates=[]),
], ids=["exception", "empty"])
def test_project_templates_failure_fails_ad(template_context):
    task_id = "t-no-templates"
    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=[11], run_agent=run_agent,
                                    get_template_context=template_context) as env:
        result = _phase1(task_id, 2)

    (report,) = result["diversity_reports"]
    assert report["ad_failed"] is True
    assert PROJECT_ID in report["error"] and "11" in report["error"]
    assert "boom secret" not in report["error"]
    # D19: templates resolved once per job; no Estratega_Adset and no checkpoint.
    assert template_context.call_count == 1
    assert run_agent.count(ESTRATEGA_ADSET) == 0
    assert env.checkpoint(task_id, ID_ADSET, "adset_templates") is None
    assert run_agent.count(COPYWRITER) == 0
    assert env.save_ads.call_count == 0
    assert env.post_to_abyssale.call_count == 0


def test_copywriter_wrong_number_of_copies_raises():
    task_id = "t-bad-copies"
    run_agent = _agents(**{COPYWRITER: lambda call: _conforming_copies(call)[:-1]})
    with patched_diversity_pipeline(ad_ids=[11], run_agent=run_agent) as env:
        with pytest.raises(AgentValidationError):
            _phase1(task_id, 2)
    assert env.checkpoint(task_id, 11, "copy") is None
    assert run_agent.count(IMAGE_PROMPTER) == 0
    assert env.save_ads.call_count == 0


# ---------------------------------------------------------------------------
# n_variants = 6 (Req 4.9, 12.19)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", ["scenario_1", "scenario_2"])
def test_six_variants(scenario):
    task_id = f"t-six-{scenario}"
    n_variants = 6
    templates = mock_template_ids()
    assert len(templates) == 3
    id_ad = SORTED_AD_IDS[2] if scenario == "scenario_2" else None
    targets = SORTED_AD_IDS if id_ad is None else [id_ad]
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents()) as env:
        result = _phase1(task_id, n_variants, id_ad=id_ad)  # no ValidationError

    assert sorted(env.save_ads.ad_ids) == targets
    for ad_id in targets:
        assert len(env.checkpoint(task_id, ad_id, "strategy")["variants"]) == n_variants
        assert len(env.checkpoint(task_id, ad_id, "copy")) == n_variants
        assert len(env.checkpoint(task_id, ad_id, "image_prompts")) == n_variants
        _assert_template_rotation(env, task_id, ad_id, SORTED_AD_IDS.index(ad_id), n_variants)
    for report in result["diversity_reports"]:
        assert report["ad_failed"] is False and report["deterministic_pass"] is True
        assert report["deterministic_errors"] == []
    assert len(result["saved_ads"]) == len(targets) * n_variants


# ---------------------------------------------------------------------------
# Ad_Templates between Ads (Decision P11, Req 4.5, 4.6, 6.12, 12.20)
# ---------------------------------------------------------------------------

_AD_TEMPLATE_ISSUE = "share Ad_Template"  # text of every AD_TEMPLATE_REPEATED issue


def _ad_template_of(env, task_id, ad_id):
    variants = env.checkpoint(task_id, ad_id, "strategy")["variants"]
    (template,) = {v["template_id"] for v in variants}
    return template


def _ad_template_errors(result):
    return [e for r in result["diversity_reports"] for e in r["deterministic_errors"]
            if _AD_TEMPLATE_ISSUE in e]


@pytest.mark.parametrize("ad_ids", [[11], [11, 22], AD_IDS], ids=["1-ad", "2-ads", "3-ads"])
def test_ad_templates_distinct_when_enough_templates(ad_ids):
    """Req 12.20 (a): N <= len(Project_Templates) → distinct Ad_Templates, no 6.12 issue."""
    task_id = f"t-tpl-distinct-{len(ad_ids)}"
    templates = mock_template_ids()
    assert len(ad_ids) <= len(templates)
    with patched_diversity_pipeline(ad_ids=ad_ids, run_agent=_agents()) as env:
        result = _phase1(task_id, 2)

    sorted_ids = sorted(ad_ids)
    order = expected_template_order(task_id)
    ad_templates = [_ad_template_of(env, task_id, ad_id) for ad_id in sorted_ids]
    assert ad_templates == order[:len(ad_ids)]
    assert len(set(ad_templates)) == len(ad_ids)
    assert _ad_template_errors(result) == []
    assert _warnings(env, f"[{task_id}]", _AD_TEMPLATE_ISSUE) == []
    assert all(r["ad_failed"] is False for r in result["diversity_reports"])
    assert sorted(env.save_ads.ad_ids) == sorted_ids


def test_ad_templates_rotate_with_warning_when_templates_exhausted():
    """Req 12.20 (b): 4 Ads and 3 templates → slots 0 and 3 share the Ad_Template, a
    warning (not a 6.12 error) is logged and the job continues with 4 save_ads."""
    task_id = "t-tpl-exhausted"
    ad_ids = [44, 22, 11, 33]
    sorted_ids = sorted(ad_ids)
    templates = mock_template_ids()
    assert len(ad_ids) == len(templates) + 1
    with patched_diversity_pipeline(ad_ids=ad_ids, run_agent=_agents()) as env:
        result = _phase1(task_id, 2)

    order = expected_template_order(task_id)
    ad_templates = [_ad_template_of(env, task_id, ad_id) for ad_id in sorted_ids]
    assert ad_templates == [order[s % len(order)] for s in range(len(ad_ids))]
    assert ad_templates[0] == ad_templates[3]
    assert len(set(ad_templates[:3])) == 3

    # Warning for the slots 0 and 3, logged by the Ads of those slots only.
    for slot in (0, 3):
        assert _warnings(env, f"[{task_id}]", f"ad={sorted_ids[slot]}", "Ad_Slots 0 and 3",
                         _AD_TEMPLATE_ISSUE)
    for slot in (1, 2):
        assert _warnings(env, f"[{task_id}]", f"ad={sorted_ids[slot]}", _AD_TEMPLATE_ISSUE) == []

    reports = result["diversity_reports"]
    assert _ad_template_errors(result) == []
    assert sorted(r["ad_id"] for r in reports) == sorted_ids
    assert all(r["ad_failed"] is False and r["deterministic_errors"] == [] for r in reports)
    assert env.save_ads.call_count == 4
    assert sorted(env.save_ads.ad_ids) == sorted_ids
    for slot, ad_id in enumerate(sorted_ids):
        _assert_template_rotation(env, task_id, ad_id, slot, 2)


@pytest.mark.parametrize("slot", [0, 1, 2])
def test_scenario_2_id_ad_keeps_scenario_1_ad_template(slot):
    """Req 12.20 (c) / P12: in Scenario_2 the Ad `id_ad` gets `order_s2[slot]`, the
    Ad_Template of its Ad_Slot in the Template_Order of the Scenario_2 job, distinct from
    the Ad_Templates `order_s2[i]` of its sibling slots."""
    s2_task = f"t-tpl-s2-{slot}"
    id_ad = SORTED_AD_IDS[slot]
    order_s2 = expected_template_order(s2_task)
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents()) as env:
        result = _phase1(s2_task, 2, id_ad=id_ad, add_variant=True, id_variant=[901])

    own = _ad_template_of(env, s2_task, id_ad)
    assert own == order_s2[slot]
    assert own not in [order_s2[i] for i in range(len(SORTED_AD_IDS)) if i != slot]
    assert env.save_ads.ad_ids == [id_ad]
    assert _ad_template_errors(result) == []
    assert _warnings(env, f"[{s2_task}]", _AD_TEMPLATE_ISSUE) == []


def test_scenario_2_extra_slot_gets_next_template_in_rotation():
    """Req 12.20 (c) / 3.6: `id_ad` absent → extra Ad_Slot len(Adset_Ads) with
    `order[len(Adset_Ads) % len(order)]`; the job is not failed."""
    task_id = "t-tpl-extra-slot"
    id_ad = 999
    order = expected_template_order(task_id)
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents()) as env:
        result = _phase1(task_id, 2, id_ad=id_ad)

    extra_slot = len(AD_IDS)
    assert [t["ad_id"] for t in _territories(env, task_id)][extra_slot] == id_ad
    _assert_template_rotation(env, task_id, id_ad, extra_slot, 2)
    assert _ad_template_of(env, task_id, id_ad) == order[len(AD_IDS) % len(order)]
    # 4 Ad_Slots > 3 templates: the extra slot shares with slot 0 → warning only.
    assert _warnings(env, f"[{task_id}]", f"ad={id_ad}", "Ad_Slots 0 and 3", _AD_TEMPLATE_ISSUE)
    (report,) = result["diversity_reports"]
    assert report["ad_failed"] is False and report["deterministic_errors"] == []
    assert env.save_ads.ad_ids == [id_ad]


# ---------------------------------------------------------------------------
# delete_variants with add_variant=False (Req 8.3, 8.5, 8.7, 12.16)
# ---------------------------------------------------------------------------

ID_VARIANT = [7001, 7002, 7003]


def test_delete_variants_once_after_abyssale():
    task_id = "t-del-ok"
    id_ad = SORTED_AD_IDS[0]
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents(),
                                    delete_variants=FakeDeleteVariants()) as env:
        _phase1(task_id, 2, id_ad=id_ad, add_variant=False, id_variant=ID_VARIANT)

    deletes = env.events.of("delete_variants")
    assert len(deletes) == 1
    assert deletes[0].arguments["variant_ids"] == ID_VARIANT
    abyssale_pos = env.events.index_of("post_to_abyssale_and_wait")
    assert env.events[abyssale_pos].arguments["ad_id"] == id_ad
    assert env.events.index_of("delete_variants") > abyssale_pos


@pytest.mark.parametrize("failing", ["save_ads", "abyssale"])
def test_delete_variants_skipped_when_save_or_abyssale_fail(failing):
    task_id = f"t-del-skip-{failing}"
    id_ad = SORTED_AD_IDS[0]
    overrides = (
        {"save_ads": FakeSaveAds([RuntimeError("save failed")])} if failing == "save_ads"
        else {"post_to_abyssale": FakePostToAbyssaleAndWait([RuntimeError("aby failed")])}
    )
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents(), **overrides) as env:
        _phase1(task_id, 2, id_ad=id_ad, add_variant=False, id_variant=ID_VARIANT)

    assert env.delete_variants.call_count == 0
    assert _warnings(env, f"[{task_id}]", f"ad={id_ad}", "delete_variants skipped")


# ---------------------------------------------------------------------------
# Image_Generator unhandled exception (Req 11.7)
# ---------------------------------------------------------------------------


def test_image_generator_exception_continues_with_save_ads_and_abyssale():
    task_id = "t-img-exc"
    ad_id = 11
    generator = FakeGenerateImagesFromPrompts([RuntimeError("generator crashed")])
    with patched_diversity_pipeline(ad_ids=[ad_id], run_agent=_agents(),
                                    generate_images=generator) as env:
        result = _phase1(task_id, 2)

    assert generator.call_count == 1
    assert env.save_ads.ad_ids == [ad_id]
    assert len(env.save_ads.payloads[0]) == 2
    assert [c.arguments["ad_id"] for c in env.post_to_abyssale.calls] == [ad_id]
    assert all(s["saved"] for s in result["saved_ads"])
    assert result["diversity_reports"][0]["ad_failed"] is False
    assert any(r.level == "ERROR" and f"[{task_id}]" in r.message and f"ad={ad_id}" in r.message
               for r in env.logs.records)


# ---------------------------------------------------------------------------
# custom_prompt (Req 8.6) and Validador with n_variants=1 (Req 7.2)
# ---------------------------------------------------------------------------


def test_custom_prompt_reaches_three_factories_but_not_validador():
    custom = "Use a playful tone."
    with patched_diversity_pipeline(ad_ids=[11, 22], run_agent=_agents()) as env:
        _phase1("t-custom", 2, custom_prompt=custom)

    for name in (ESTRATEGA_ADSET, COPYWRITER, IMAGE_PROMPTER):
        prompts = env.factories.custom_prompts(name)
        assert prompts and all(p == custom for p in prompts), name
    validador_prompts = env.factories.custom_prompts(VALIDADOR_ADSET)
    assert validador_prompts and all(p is None for p in validador_prompts)
    assert env.factories.count(VALIDADOR) == 0


def test_validador_runs_with_single_variant():
    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=[11, 22], run_agent=run_agent) as env:
        result = _phase1("t-one-variant", 1)

    assert run_agent.count(VALIDADOR_ADSET) == 2
    assert env.factories.count(VALIDADOR_ADSET) == 2 and env.factories.count(VALIDADOR) == 0
    assert [r["iterations"] for r in result["diversity_reports"]] == [1, 1]


# ---------------------------------------------------------------------------
# diversity_reports (Req 7.12)
# ---------------------------------------------------------------------------

REPORT_KEYS = {"ad_id", "plan_id", "deterministic_pass", "deterministic_errors",
               "deterministic_warnings", "overall_pass", "iterations", "subset_to_regenerate"}
RESULT_KEYS = {"variant_job_id", "id_adset", "status", "abyssale_batch_ids", "proposals",
               "validation_reports", "saved_ads", "diversity_reports"}


def test_diversity_reports_shape():
    task_id = "t-reports"
    run_agent = _agents(**{VALIDADOR_ADSET: {"overall_pass": False, "subset_to_regenerate": []}})
    with patched_diversity_pipeline(ad_ids=[11, 22], run_agent=run_agent):
        result = _phase1(task_id, 2)

    assert RESULT_KEYS <= set(result)
    assert result["variant_job_id"] == task_id and result["id_adset"] == ID_ADSET
    reports = sorted(result["diversity_reports"], key=lambda r: r["ad_id"])
    assert [r["ad_id"] for r in reports] == [11, 22]
    for report in reports:
        assert REPORT_KEYS <= set(report)
        assert report["plan_id"] == f"plan_ad_{report['ad_id']}"
        assert report["deterministic_pass"] is True
        # Semantic failure with empty subset ends the loop but does not abort (Req 7.7).
        assert report["overall_pass"] is False
        assert report["iterations"] == 1
        assert report["subset_to_regenerate"] == []
    assert len(result["saved_ads"]) == 4


# ---------------------------------------------------------------------------
# Job 259a13a7: one Ad failing must not redo the finished Ads on the Celery retry
# ---------------------------------------------------------------------------


def test_finished_ad_is_not_redone_when_another_ad_fails():
    task_id = "t-ad-result"
    bad_for_22 = lambda call: [] if "ad_id=22 " in call.message else _conforming_copies(call)
    run_agent = _agents(**{COPYWRITER: bad_for_22})
    with patched_diversity_pipeline(ad_ids=[11, 22], run_agent=run_agent) as env:
        with pytest.raises(AgentValidationError):
            _phase1(task_id, 2)
        assert env.save_ads.ad_ids == [11]
        assert [c.arguments["ad_id"] for c in env.post_to_abyssale.calls] == [11]
        assert env.checkpoint(task_id, 11, "ad_result")["saved_ads"]

        # Celery retry of the same task_id: the Copywriter now answers ad 22 correctly.
        run_agent.set_default(COPYWRITER, _conforming_copies)
        result = _phase1(task_id, 2)

    # Ad 11 was neither saved nor submitted to Abyssale again.
    assert env.save_ads.ad_ids == [11, 22]
    assert [c.arguments["ad_id"] for c in env.post_to_abyssale.calls] == [11, 22]
    assert sorted(r["ad_id"] for r in result["diversity_reports"]) == [11, 22]
    assert len(result["saved_ads"]) == 4


def test_retryable_agent_codes():
    for code in ("ERR_EMPTY_RESPONSE", "ERR_VARIANT_SHAPE", "ERR_INVALID_JSON",
                 "ERR_COPY_INVALID_TYPE_CTA", "ERR_COPY_MISSING_CTA", "ERR_PROMPT_INVALID_TYPE_IMAGE_PROMPTS"):
        assert jrs._is_retryable_agent_code(code), code
    for code in ("ERR_PROCESSING_LLM", "ERR_MISSING_CONCEPT", None, ""):
        assert not jrs._is_retryable_agent_code(code), code


def _templates_without_image_elements(template_id):
    """`_MOCK_TEMPLATES` where `template_id` keeps its `image` elements only under a
    decorative name (P15, Req 15.2): its Image_Elements are `[]`."""
    templates = mock_templates()["templates"]
    (target,) = [t for t in templates if str(t["id"]) == template_id]
    for element in target["elements"]:
        if element.get("type") == "image":
            element["name"] = f"gradient_{element['name']}"
    assert expected_image_elements(target) == []
    return templates


def test_template_without_image_elements_does_not_fail_the_ad():
    """P15 (Req 15.4, 15.5, 12.3): the Ad's Template_Definition has no Image_Elements
    (only decorative `image` layers): the Image_Prompter message carries
    `"elements": []`, the Ad is accepted with `image_prompts: []`, no image is generated
    and save_ads / Abyssale still run."""
    task_id = "t-no-image-elements"
    template_id = expected_template_order(task_id)[0]  # single Ad → ad_slot 0
    definitions = FakeGetATemplateDefinition(_templates_without_image_elements(template_id))
    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=[11], run_agent=run_agent,
                                    get_a_template_definition=definitions) as env:
        result = _phase1(task_id, 2)

    messages = run_agent.messages_for(IMAGE_PROMPTER)
    assert messages
    for message in messages:
        line = image_elements_from_message(message)
        assert line is not None
        assert line["template_id"] == template_id
        assert line["elements"] == []
    (report,) = result["diversity_reports"]
    assert report["ad_failed"] is False
    assert all(p["image_prompts"] == [] for p in env.checkpoint(task_id, 11, "image_prompts"))
    assert env.generate_images.call_count == 0
    assert env.save_ads.ad_ids == [11]
    assert [c.arguments["ad_id"] for c in env.post_to_abyssale.calls] == [11]
    assert len(result["saved_ads"]) == 2


# ---------------------------------------------------------------------------
# Template_Order per job (Decision P12, D18, D19; Req 2.7, 4.10–4.13, 12.20 (e)–(h))
# ---------------------------------------------------------------------------

# Two concrete task_ids whose seeded Template_Orders differ (checked in the test).
ORDER_TASK_A, ORDER_TASK_B = "t-order-a", "t-order-b"


def _adset_templates_key(task_id):
    return cp_key(task_id, ID_ADSET, "adset_templates")


def _job_ad_templates(env, task_id, ad_ids):
    return [_ad_template_of(env, task_id, ad_id) for ad_id in sorted(ad_ids)]


def test_same_task_id_gives_same_template_order():
    """Req 12.20 (e): two runs with the same task_id store the same Template_Order,
    which is a permutation of the `_MOCK_TEMPLATES` ids."""
    task_id = "t-order-same"
    stored = []
    for _ in range(2):
        with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents()) as env:
            _phase1(task_id, 2)
            stored.append((env.checkpoint(task_id, ID_ADSET, "adset_templates"),
                           _job_ad_templates(env, task_id, AD_IDS)))

    (cp1, ads1), (cp2, ads2) = stored
    assert cp1 == cp2
    assert ads1 == ads2
    assert cp1["template_order"] == expected_template_order(task_id)
    assert sorted(cp1["template_order"]) == sorted(mock_template_ids())
    assert cp1["project_templates"] == mock_template_ids()


def test_different_task_ids_give_different_ad_templates():
    """Req 12.20 (f): two concrete task_ids yield different Template_Orders and
    therefore different Ad_Templates for the same Ad_Slots."""
    assert expected_template_order(ORDER_TASK_A) != expected_template_order(ORDER_TASK_B)
    assigned = {}
    for task_id in (ORDER_TASK_A, ORDER_TASK_B):
        with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents()) as env:
            _phase1(task_id, 2)
            assigned[task_id] = _job_ad_templates(env, task_id, AD_IDS)
        assert assigned[task_id] == expected_template_order(task_id)
    assert assigned[ORDER_TASK_A] != assigned[ORDER_TASK_B]


def test_all_ads_share_template_order_and_templates_resolved_once():
    """Req 12.20 (g) / 4.10, 4.11: N >= 2 Ads use the same Template_Order and
    get_template_context is called once per job; adset_templates precedes every
    strategy write."""
    task_id = "t-order-shared"
    template_context = FakeGetTemplateContext()
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents(),
                                    get_template_context=template_context) as env:
        _phase1(task_id, 2)

    assert template_context.call_count == 1
    order = expected_template_order(task_id)
    for ad_slot, ad_id in enumerate(SORTED_AD_IDS):
        plan = env.checkpoint(task_id, ad_id, "strategy")
        assert plan["_project_templates"] == mock_template_ids()
        _assert_template_rotation(env, task_id, ad_id, ad_slot, 2)
    assert env.checkpoint(task_id, ID_ADSET, "adset_templates")["template_order"] == order

    # Req 4.12 / D18: adset_templates is written (once) before any strategy checkpoint.
    keys = env.redis.written_keys
    strategy_positions = [i for i, k in enumerate(keys) if k.endswith(":strategy")]
    assert len(strategy_positions) == len(AD_IDS)
    assert keys.count(_adset_templates_key(task_id)) == 1
    assert keys.index(_adset_templates_key(task_id)) < min(strategy_positions)


def test_retry_reuses_adset_templates_checkpoint():
    """Req 12.20 (h) / 4.12: with `adset_templates` preloaded (an order different from
    the seeded one) the retry neither calls get_template_context nor recomputes."""
    task_id = "t-order-retry"
    templates = mock_template_ids()
    seeded = expected_template_order(task_id)
    preloaded = list(reversed(seeded))
    assert preloaded != seeded and sorted(preloaded) == sorted(templates)
    redis = FakeRedis()
    redis.seed(_adset_templates_key(task_id),
               {"project_templates": templates, "template_order": preloaded})
    template_context = FakeGetTemplateContext()
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=_agents(), redis=redis,
                                    get_template_context=template_context) as env:
        result = _phase1(task_id, 2)

    assert template_context.call_count == 0
    assert _adset_templates_key(task_id) not in env.redis.written_keys
    assert _job_ad_templates(env, task_id, AD_IDS) == preloaded
    for ad_id in SORTED_AD_IDS:
        copies = env.checkpoint(task_id, ad_id, "copy")
        assert {c["template_id"] for c in copies} == {_ad_template_of(env, task_id, ad_id)}
    assert all(r["ad_failed"] is False for r in result["diversity_reports"])


def test_failed_template_resolution_fails_every_ad():
    """Req 4.13 / D19: failed resolution with N=2 → each Ad `ad_failed` with project_id
    and ad_id in the message, no Estratega_Adset/Copywriter call, no adset_templates."""
    task_id = "t-order-fail"
    ad_ids = [22, 11]
    template_context = FakeGetTemplateContext(script=[RuntimeError("sinergia down")])
    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=ad_ids, run_agent=run_agent,
                                    get_template_context=template_context) as env:
        result = _phase1(task_id, 2)

    reports = sorted(result["diversity_reports"], key=lambda r: r["ad_id"])
    assert [r["ad_id"] for r in reports] == sorted(ad_ids)
    for report in reports:
        assert report["ad_failed"] is True
        assert f"project_id={PROJECT_ID}" in report["error"]
        assert f"ad_id={report['ad_id']}" in report["error"]
    assert template_context.call_count == 1
    assert run_agent.count(ESTRATEGA_ADSET) == 0
    assert run_agent.count(COPYWRITER) == 0
    assert env.checkpoint(task_id, ID_ADSET, "adset_templates") is None
    assert not [k for k in env.redis.written_keys if k.endswith((":adset_templates", ":strategy"))]
    assert env.save_ads.call_count == 0


def test_incoherent_strategy_checkpoint_is_ignored():
    """Req 4.12 / D18: a `strategy` checkpoint whose Ad_Template differs from
    order[ad_slot] (pre-P12 checkpoint) is ignored with a warning and recomputed."""
    task_id = "t-order-incoherent"
    ad_id = 11
    order = expected_template_order(task_id)
    with patched_diversity_pipeline(ad_ids=[ad_id], run_agent=_agents()) as env0:
        _phase1(task_id, 2)
        stale = env0.checkpoint(task_id, ad_id, "strategy")
    wrong = next(t for t in order if t != order[0])
    for slot in stale["variants"]:
        slot["template_id"] = wrong
    redis = FakeRedis()
    redis.seed_checkpoint(task_id, ad_id, "strategy", stale)

    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=[ad_id], run_agent=run_agent, redis=redis) as env:
        result = _phase1(task_id, 2)

    assert run_agent.count(ESTRATEGA_ADSET) == 1
    assert _warnings(env, f"[{task_id}]", f"ad={ad_id}", "incoherent with Template_Order")
    _assert_template_rotation(env, task_id, ad_id, 0, 2)
    assert result["diversity_reports"][0]["ad_failed"] is False


def test_flag_off_does_not_write_adset_templates():
    """Req 2.7: with the Diversity_Flag off (Legacy_Path) no adset_templates is written."""
    from tests.test_phase1_legacy_golden import ID_AD, N_VARIANTS, _fake_run_agent

    task_id = "t-order-legacy"
    with patched_diversity_pipeline(adset_context=make_adset_context(),
                                    run_agent=_fake_run_agent(), diversity_flag=False) as env:
        asyncio.run(jrs._run_phase1(FakeTask(task_id), task_id, ID_ADSET, N_VARIANTS,
                                    PROJECT_ID, id_ad=ID_AD))

    assert env.run_agent.count(ESTRATEGA_ADSET) == 0
    assert env.run_agent.count(COPYWRITER) == 1
    assert not [k for k in env.redis.written_keys if k.endswith(":adset_templates")]
    assert env.checkpoint(task_id, ID_ADSET, "adset_templates") is None


# ---------------------------------------------------------------------------
# Validador_Adset (Decision P13, D20, D21; Req 7.14, 8.6, 12.22, 13.2, 13.5)
# ---------------------------------------------------------------------------


class _ForbiddenTool:
    """Stand-in for `check_diversity_and_fidelity`: records and fails if ever called."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise AssertionError("check_diversity_and_fidelity must not run on the Diversity_Path")


def _forbid_check_diversity(fake):
    return [("agents.tools.validation_tools", "check_diversity_and_fidelity", fake),
            ("agents.validador_agent", "check_diversity_and_fidelity", fake)]


def test_diversity_path_uses_validador_adset_without_tools():
    """Req 12.22 / 13.2 / 8.6: the Diversity_Path creates the Validador_Adset (no
    custom_prompt, `tools == []`), never `make_validador_agent` nor
    `check_diversity_and_fidelity`."""
    forbidden = _ForbiddenTool()
    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=run_agent,
                                    extra_patches=_forbid_check_diversity(forbidden)) as env:
        result = _phase1("t-p13-validador", 2, custom_prompt="Use a playful tone.")

    factory = env.factories[VALIDADOR_ADSET]
    assert factory.call_count == len(AD_IDS)            # lazily, once per Ad
    assert factory.custom_prompts == [None] * len(AD_IDS)
    assert all(agent.tools == [] for agent in factory.agents)
    calls = run_agent.calls_for(VALIDADOR_ADSET)
    assert len(calls) == len(AD_IDS)
    assert all(any(c.agent is a for a in factory.agents) for c in calls)
    assert all(c.agent.tools == [] for c in calls)
    assert env.factories.count(VALIDADOR) == 0
    assert run_agent.count(VALIDADOR) == 0
    assert forbidden.calls == []
    assert all(r["ad_failed"] is False for r in result["diversity_reports"])


def test_flag_off_legacy_path_still_creates_make_validador_agent():
    """Req 12.22 / 13.5: with the Diversity_Flag off the Legacy_Path creates the legacy
    Validador with `make_validador_agent()` and never the Validador_Adset."""
    from tests.test_phase1_legacy_golden import ID_AD, N_VARIANTS, _fake_run_agent

    task_id = "t-p13-legacy"
    with patched_diversity_pipeline(adset_context=make_adset_context(),
                                    run_agent=_fake_run_agent(), diversity_flag=False) as env:
        try:
            asyncio.run(jrs._run_phase1(FakeTask(task_id), task_id, ID_ADSET, N_VARIANTS,
                                        PROJECT_ID, id_ad=ID_AD))
        except NameError as exc:
            # Pre-existing Legacy_Path issue (billing code of commit 3f1b980c without the
            # AdsMeter definitions): `meter` is undefined after image generation. The
            # Validador factory runs before that line, so the call is still checked.
            if "meter" not in str(exc):
                raise

    assert env.factories.count(VALIDADOR) == 1
    assert env.factories.custom_prompts(VALIDADOR) == [None]
    assert env.factories.count(VALIDADOR_ADSET) == 0
    assert env.run_agent.count(VALIDADOR_ADSET) == 0


def test_result_proposals_keep_full_image_request():
    """Req 7.14 / D21: the job's `proposals` keep `image_request` untouched; only the
    Validador_Adset message drops it."""
    task_id = "t-p13-image-request"
    url = "https://cdn.example.com/products/secret-p1.png"
    image_request = {"technical_specs": {"product_image_sources": [url]}, "style": "studio"}

    def prompts_with_request(call):
        out = _conforming_prompts(call)
        for p in out:
            for item in p["image_prompts"]:
                item["image_request"] = image_request
        return out

    run_agent = _agents(**{IMAGE_PROMPTER: prompts_with_request})
    with patched_diversity_pipeline(ad_ids=[11, 22], run_agent=run_agent):
        result = _phase1(task_id, 2)

    proposals = result["proposals"]
    assert len(proposals) == 4
    for proposal in proposals:
        assert proposal["image_prompts"]
        assert all(item["image_request"] == image_request for item in proposal["image_prompts"])
    for message in run_agent.messages_for(VALIDADOR_ADSET):
        assert "image_request" not in message and url not in message


# ---------------------------------------------------------------------------
# Variant_Angles (Decision P14, D22; Req 6.11, 6.13, 12.26, 12.28, 14.5)
# ---------------------------------------------------------------------------


def _copy_slots(run_agent, ad_id):
    (message,) = [m for m in run_agent.messages_for(COPYWRITER)
                  if all(s["variant_key"].startswith(f"plan_ad_{ad_id}_v")
                         for s in _slots_from_message(m))]
    return message, _slots_from_message(message)


def test_copywriter_message_has_variant_key_and_angle_per_slot():
    """Req 12.26 / 14.6: the initial Copywriter message carries, per Variant_Slot, its
    `variant_key` with its Variant_Angle, plus the instruction to follow it."""
    from services.adset_diversity import VARIANT_ANGLES_BLOCK

    task_id = "t-p14-copy-angles"
    n_variants = 3
    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=AD_IDS, run_agent=run_agent) as env:
        _phase1(task_id, n_variants)

    assert run_agent.count(COPYWRITER) == len(AD_IDS)
    for ad_id in SORTED_AD_IDS:
        message, slots = _copy_slots(run_agent, ad_id)
        template = _ad_template_of(env, task_id, ad_id)
        expected = expected_slots(f"plan_ad_{ad_id}", n_variants, template)
        assert [(s["variant_key"], s["angle"]) for s in slots] == \
            [(s["variant_key"], s["angle"]) for s in expected]
        assert len({json.dumps(s["angle"], sort_keys=True) for s in slots}) == n_variants
        assert VARIANT_ANGLES_BLOCK in message


def _seeded_redis(task_id, ad_id, strategy):
    """Fresh FakeRedis with the job checkpoints of a previous run of `task_id`, except
    `copy`/`image_prompts`/`ad_result`, and with `strategy` replaced."""
    with patched_diversity_pipeline(ad_ids=[ad_id], run_agent=_agents()) as env0:
        _phase1(task_id, 2)
        territories = env0.checkpoint(task_id, ID_ADSET, "adset_territories")
        templates = env0.checkpoint(task_id, ID_ADSET, "adset_templates")
        plan = env0.checkpoint(task_id, ad_id, "strategy")
    assert territories and templates and plan
    redis = FakeRedis()
    redis.seed_checkpoint(task_id, ID_ADSET, "adset_territories", territories)
    redis.seed_checkpoint(task_id, ID_ADSET, "adset_templates", templates)
    redis.seed_checkpoint(task_id, ad_id, "strategy", strategy(plan))
    return redis


@pytest.mark.parametrize("variant", ["with_angles", "without_angles"])
def test_strategy_checkpoint_angles_on_retry(variant):
    """Req 12.28 / 14.5: a `strategy` checkpoint with valid angles is reused as stored;
    without angles they are completed with `assign_variant_angles` (same as a fresh
    computation). Neither case calls the Estratega_Adset nor get_template_context."""
    from services.adset_diversity import assign_variant_angles

    task_id = f"t-p14-cp-{variant}"
    ad_id = 11
    plan_id = f"plan_ad_{ad_id}"
    fresh = assign_variant_angles(plan_id, 2)

    def edit(plan):
        for slot, angle in zip(plan["variants"], reversed(fresh)):
            if variant == "with_angles":
                slot["angle"] = angle            # valid, but not the fresh order
            else:
                slot.pop("angle", None)
        return plan

    redis = _seeded_redis(task_id, ad_id, edit)
    template_context = FakeGetTemplateContext()
    run_agent = _agents()
    with patched_diversity_pipeline(ad_ids=[ad_id], run_agent=run_agent, redis=redis,
                                    get_template_context=template_context) as env:
        result = _phase1(task_id, 2)

    expected = list(reversed(fresh)) if variant == "with_angles" else fresh
    assert run_agent.count(ESTRATEGA_ADSET) == 0
    assert template_context.call_count == 0
    assert [s["angle"] for s in env.checkpoint(task_id, ad_id, "strategy")["variants"]] == expected
    _, slots = _copy_slots(run_agent, ad_id)
    assert [s["angle"] for s in slots] == expected
    strategy_writes = [k for k in env.redis.written_keys if k.endswith(f":{ad_id}:strategy")]
    if variant == "with_angles":
        assert strategy_writes == []
    else:
        assert len(strategy_writes) == 1
        assert _warnings(env, f"[{task_id}]", f"ad={ad_id}", "Variant_Angles")
    assert result["diversity_reports"][0]["ad_failed"] is False


@pytest.mark.parametrize("bad", ["foreign", "repeated"])
def test_invalid_variant_angle_fails_ad_before_copywriter(bad):
    """Req 6.11 / 6.13: an invalid Variant_Angle (outside Angle_Vocabulary or repeated
    with n_variants <= len(Angle_Vocabulary)), injected by patching
    `assign_variant_angles`, fails the Ad without calling the Copywriter."""
    import services.adset_diversity as adset_diversity

    real = adset_diversity.assign_variant_angles
    foreign = {"hook": "zz_hook", "headline_structure": "zz_headline", "copy_length": "short"}

    def broken(plan_id, n_variants):
        angles = real(plan_id, n_variants)
        if bad == "foreign":
            return [foreign] + angles[1:]
        return [angles[0]] * n_variants

    task_id = f"t-p14-bad-angle-{bad}"
    ad_id = 11
    run_agent = _agents()
    with patched_diversity_pipeline(
        ad_ids=[ad_id], run_agent=run_agent,
        extra_patches=[(adset_diversity, "assign_variant_angles", broken)],
    ) as env:
        result = _phase1(task_id, 2)

    (report,) = result["diversity_reports"]
    assert report["ad_failed"] is True
    assert report["deterministic_errors"]
    needle = "is not in Angle_Vocabulary" if bad == "foreign" else "angle"
    assert any(needle in e for e in report["deterministic_errors"])
    assert run_agent.count(ESTRATEGA_ADSET) == 1
    assert run_agent.count(COPYWRITER) == 0
    assert run_agent.count(IMAGE_PROMPTER) == 0
    assert env.generate_images.call_count == 0
    assert env.save_ads.call_count == 0
    assert env.checkpoint(task_id, ad_id, "strategy") is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
