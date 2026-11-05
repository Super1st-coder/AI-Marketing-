"""Unit tests for `job_runner_service._build_or_load_creative_plan` (adset-creative-diversity,
task 11.2; Req 4.1–4.8, 6.11, 8.6).

Runs the real function on top of FakeRedis / FakeRunAgent: no network, Redis or LLM.
The job templates arrive in `_DiversityAdInput.templates` (`_JobTemplates`, P12, D18, D19);
FakeGetTemplateContext only checks that the Creative_Plan never calls it (task 20.2).

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_creative_plan.py
    PYTHONPATH=. python -m tests.test_adset_diversity_creative_plan
"""
import asyncio
import dataclasses
import json

import pytest

import services.job_runner_service as jrs
from core.validation import AgentValidationError
from services.adset_diversity import (
    DEFAULT_DECORATIVE_IMAGE_PATTERNS,
    bind_territories,
    resolve_project_templates,
    template_order,
)
from services.territory_assignment import assign_territories
from tests._diversity_pipeline_fakes import (
    ESTRATEGA_ADSET,
    FakeAgentFactories,
    FakeGetATemplateDefinition,
    FakeGetTemplateContext,
    FakeRedis,
    FakeRunAgent,
    expected_slots,
    expected_template_order,
    make_adset_context,
    mock_template_ids,
    mock_templates,
)

TASK_ID = "task-creative-plan"
ID_ADSET = 7
PROJECT_ID = "test-project-id"
AD_IDS = [101, 102]
CUSTOM_PROMPT = "be bold"


def _territories(ctx):
    assigned = assign_territories(ctx, n_ads=len(AD_IDS), adset_id=ID_ADSET, n_variantes=1)
    return bind_territories(assigned, AD_IDS)


def _job_templates(templates=None, template_script=None) -> "jrs._JobTemplates":
    """`_JobTemplates` of the job as `_load_or_resolve_templates` would build it (P12, D18,
    D19): the first scripted item (exception / `ok=False`) or `{"ok": True, "templates": ...}`
    → resolve_project_templates → template_order(..., TASK_ID); failures carry the cause."""
    script = list(template_script or [])
    if script and isinstance(script[0], BaseException):
        return jrs._JobTemplates((), (), failure=f"get_template_context raised {type(script[0]).__name__}")
    context = script[0] if script else {
        "ok": True,
        "templates": templates if templates is not None else mock_templates()["templates"],
    }
    if isinstance(context, dict) and context.get("ok") is False:
        return jrs._JobTemplates((), (), failure="get_template_context returned ok=False")
    project_templates = resolve_project_templates(context)
    if not project_templates:
        return jrs._JobTemplates((), (), failure="get_template_context returned no templates")
    order = template_order(project_templates, TASK_ID)
    return jrs._JobTemplates(tuple(project_templates), tuple(order))


def _setup(monkeypatch, *, concept="A concept", templates=None, template_script=None,
           n_variants=2, redis=None, ad_index=0, territories=None):
    ctx = make_adset_context(AD_IDS)
    terr = territories if territories is not None else _territories(ctx)
    run_agent = FakeRunAgent({ESTRATEGA_ADSET: [[{"index": 0, "concept": concept}]]})
    redis = redis or FakeRedis()
    monkeypatch.setattr(jrs, "_run_agent", run_agent)
    monkeypatch.setattr(jrs, "_redis", lambda: redis)
    factories = FakeAgentFactories()
    # The Creative_Plan never calls get_template_context (P12, D19): the fake only records
    # that it is not invoked; the job templates travel in `_DiversityAdInput.templates`.
    get_tc = FakeGetTemplateContext()
    deps = jrs._DiversityDeps(
        get_template_context=get_tc, delete_variants=None, validate_ctas=None,
        save_ads_programmatically=None, generate_images=None, build_abyssale_payload=None,
        post_to_abyssale_and_wait=None,
        make_estratega_adset_agent=factories[ESTRATEGA_ADSET],
        make_copywriter_agent=None, make_image_prompter_agent=None,
        make_validador_adset_agent=None, progress=lambda *_: None,
        template_definitions=jrs._JobTemplateDefinitions(
            FakeGetATemplateDefinition(), DEFAULT_DECORATIVE_IMAGE_PATTERNS),
    )
    job = jrs._DiversityJob(
        task=None, task_id=TASK_ID, id_adset=ID_ADSET, n_variants=n_variants,
        project_id=PROJECT_ID, id_ad=None, custom_prompt=CUSTOM_PROMPT, add_variant=True,
        id_variant=None, adset_context=ctx, adset_context_json=json.dumps(ctx),
    )
    t = terr[ad_index]
    ad = jrs._DiversityAdInput(
        ad_id=AD_IDS[ad_index], ad_slot=ad_index, territory=t,
        all_territories=tuple(terr), forbidden=tuple(t.territorio_prohibido),
        templates=_job_templates(templates, template_script),
    )
    return deps, job, ad, run_agent, redis, factories, get_tc


def _run(deps, ad, job):
    return asyncio.run(jrs._build_or_load_creative_plan(deps, ad, job))


def _strategy_key(ad_id):
    return jrs._cp_key(TASK_ID, ad_id, "strategy")


def test_builds_plan_with_rotated_templates_and_stores_checkpoint(monkeypatch):
    deps, job, ad, run_agent, redis, factories, _ = _setup(monkeypatch, ad_index=1, n_variants=2)
    plan, templates = _run(deps, ad, job)

    ids = mock_template_ids()
    order = expected_template_order(TASK_ID)
    # Project_Templates keep Sinergia's order (D14); variants use the Template_Order (P12).
    assert templates == ids
    assert plan["id"] == "plan_ad_102"
    assert plan["concept"] == "A concept"
    assert plan["_project_templates"] == ids
    # P11/P12: all variants use order[ad_slot % len] with ad_slot=1 (Req 4.5, 4.6, 12.19);
    # each slot carries its Variant_Angle (P14, D22; Req 14.1).
    assert plan["variants"] == expected_slots("plan_ad_102", 2, order[1 % len(order)])
    # Territory values preserved (Req 4.3).
    assert plan["target_insight"] == ad.territory.territory.anchor_primary.text
    assert plan["_territory"]["territorio_prohibido"] == list(ad.forbidden)
    # One estratega call with the single-territory message (Req 4.2) and custom_prompt (Req 8.6).
    assert run_agent.count(ESTRATEGA_ADSET) == 1
    assert "FULL ADSET CONTEXT" in run_agent.messages_for(ESTRATEGA_ADSET)[0]
    assert factories.custom_prompts(ESTRATEGA_ADSET) == [CUSTOM_PROMPT]
    # Shared territory not mutated.
    assert ad.territory.concept in (None, "")
    assert json.loads(redis.data[_strategy_key(102)]) == plan


def test_checkpoint_reused_without_agent_nor_templates(monkeypatch):
    deps, job, ad, run_agent, redis, _, get_tc = _setup(monkeypatch)
    first, _ = _run(deps, ad, job)
    run_agent.push(ESTRATEGA_ADSET, AssertionError("must not be called"))

    # Same `ad.templates` → the checkpoint's Variant_Slots match
    # ad_template_for_slot(ad_slot, template_order), so it is reused (Req 4.8, 4.12).
    plan, templates = _run(deps, ad, job)
    assert plan == first
    assert templates == first["_project_templates"]
    assert run_agent.count(ESTRATEGA_ADSET) == 1
    # The Creative_Plan never calls get_template_context (P12, D19).
    assert get_tc.call_count == 0


def test_foreign_checkpoint_is_ignored(monkeypatch):
    redis = FakeRedis({_strategy_key(101): [{"id": "plan_1"}]})  # legacy list shape (D10)
    deps, job, ad, run_agent, _, _, _ = _setup(monkeypatch, redis=redis)
    plan, _ = _run(deps, ad, job)
    assert plan["id"] == "plan_ad_101"
    assert run_agent.count(ESTRATEGA_ADSET) == 1


@pytest.mark.parametrize("concept", ["", "   "])
def test_empty_concept_raises_agent_validation_error(monkeypatch, concept):
    deps, job, ad, _, redis, _, get_tc = _setup(monkeypatch, concept=concept)
    with pytest.raises(AgentValidationError):
        _run(deps, ad, job)
    assert get_tc.call_count == 0
    assert _strategy_key(101) not in redis.data


@pytest.mark.parametrize("script,templates", [
    ([RuntimeError("secret https://x?X-Amz-Signature=abc")], None),
    ([{"ok": False, "error": "boom"}], None),
    (None, []),
])
def test_template_failures_fail_the_ad(monkeypatch, script, templates):
    deps, job, ad, _, redis, _, _ = _setup(monkeypatch, templates=templates, template_script=script)
    with pytest.raises(jrs._AdDiversityFailure) as info:
        _run(deps, ad, job)
    assert PROJECT_ID in info.value.message and "101" in info.value.message
    assert "X-Amz-Signature" not in info.value.message
    assert _strategy_key(101) not in redis.data


def test_duplicate_template_ids_are_deduplicated_and_the_ad_does_not_fail(monkeypatch):
    # Two templates with the same id deduplicate to a single Project_Template; every variant
    # uses T1 and the Ad does not fail (Req 4.5, 4.7). With 2 Ad_Slots and 1 template rule 6.12
    # only yields a warning.
    tpl = [{"id": "T1"}, {"id": "T1"}]
    deps, job, ad, _, redis, _, _ = _setup(monkeypatch, templates=tpl, n_variants=2)
    plan, templates = _run(deps, ad, job)
    assert templates == ["T1"]
    assert plan["_project_templates"] == ["T1"]
    assert [v["template_id"] for v in plan["variants"]] == ["T1", "T1"]
    assert json.loads(redis.data[_strategy_key(101)]) == plan


def test_repeated_anchor_with_sibling_fails_the_ad(monkeypatch):
    ctx = make_adset_context(AD_IDS)
    terr = _territories(ctx)
    clone = terr[0].model_copy(deep=True, update={"ad_id": AD_IDS[1]})
    deps, job, ad, _, redis, _, _ = _setup(monkeypatch, territories=[terr[0], clone])
    with pytest.raises(jrs._AdDiversityFailure) as info:
        _run(deps, ad, job)
    assert any("Ad_Slots 0 and 1" in e for e in info.value.deterministic_errors)
    assert _strategy_key(101) not in redis.data


def test_exhausted_templates_log_ad_template_warning(monkeypatch):
    # 2 Ad_Slots, 1 Project_Template → rule 6.12 is a warning (Req 6.10), the Ad continues.
    from loguru import logger

    deps, job, ad, run_agent, redis, _, _ = _setup(monkeypatch, templates=[{"id": "T1"}], ad_index=1)
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(str(m)), level="WARNING")
    try:
        plan, _ = _run(deps, ad, job)
    finally:
        logger.remove(sink_id)
    assert plan["id"] == "plan_ad_102"
    assert [v["template_id"] for v in plan["variants"]] == ["T1", "T1"]
    assert any(
        f"[{TASK_ID}]" in m and "Ad_Slots 0 and 1" in m and "share Ad_Template 'T1'" in m
        for m in messages
    )
    assert run_agent.agent_names == [ESTRATEGA_ADSET]
    assert _strategy_key(102) in redis.data


def test_repeated_ad_template_with_enough_templates_fails_the_ad(monkeypatch):
    # A regression in the slot → Ad_Template map (D16) with enough templates is an error
    # (Req 6.12, 6.11): the Ad fails before the Copywriter and no checkpoint is stored.
    import services.adset_diversity as ad_mod

    monkeypatch.setattr(ad_mod, "slot_ad_templates", lambda n, tpls: [tpls[0]] * n)
    deps, job, ad, run_agent, redis, _, _ = _setup(monkeypatch)
    t0 = expected_template_order(TASK_ID)[0]  # the patch receives the Template_Order (P12)
    with pytest.raises(jrs._AdDiversityFailure) as info:
        _run(deps, ad, job)
    failure = info.value
    assert any(
        "Ad_Slots 0 and 1" in e and f"share Ad_Template '{t0}'" in e
        for e in failure.deterministic_errors
    )
    assert not any("share Ad_Template" in w for w in failure.deterministic_warnings)
    # No Copywriter / Image_Prompter: only the Estratega ran (Req 6.11).
    assert run_agent.agent_names == [ESTRATEGA_ADSET]
    assert _strategy_key(101) not in redis.data
    # The failed Diversity_Report carries the 6.12 issue (D4, D5).
    report = jrs._failed_diversity_report(101, "plan_ad_101", failure)
    assert report["ad_failed"] is True and report["deterministic_pass"] is False
    assert report["deterministic_errors"] == failure.deterministic_errors


def test_ad_template_warning_reaches_failure_report_when_the_ad_fails(monkeypatch):
    # 1 Project_Template (6.12 → warning, Req 6.10) plus a repeated anchor (error): the Ad
    # fails and the 6.12 warning travels in deterministic_warnings, not in the errors.
    ctx = make_adset_context(AD_IDS)
    terr = _territories(ctx)
    clone = terr[0].model_copy(deep=True, update={"ad_id": AD_IDS[1]})
    deps, job, ad, run_agent, redis, _, _ = _setup(
        monkeypatch, templates=[{"id": "T1"}], territories=[terr[0], clone],
    )
    with pytest.raises(jrs._AdDiversityFailure) as info:
        _run(deps, ad, job)
    failure = info.value
    assert any("share Ad_Template 'T1'" in w for w in failure.deterministic_warnings)
    assert not any("share Ad_Template" in e for e in failure.deterministic_errors)
    assert failure.deterministic_errors
    assert run_agent.agent_names == [ESTRATEGA_ADSET]
    assert _strategy_key(101) not in redis.data
    report = jrs._failed_diversity_report(101, "plan_ad_101", failure)
    assert report["deterministic_warnings"] == failure.deterministic_warnings


def test_ad_template_check_not_rerun_from_checkpoint(monkeypatch):
    import services.diversity_checker as dc

    deps, job, ad, _, _, _, _ = _setup(monkeypatch)
    first, _ = _run(deps, ad, job)

    def _boom(*_a, **_k):
        raise AssertionError("check_ad_templates must not run from checkpoint (D16)")

    monkeypatch.setattr(dc, "check_ad_templates", _boom)
    plan, _ = _run(deps, ad, job)
    assert plan == first


# ---------------------------------------------------------------------------
# Job templates (`_JobTemplates`) and `strategy` checkpoint coherence
# (task 22.2; Req 4.7, 4.8, 4.13; P12, D18, D19)
# ---------------------------------------------------------------------------

def _replace_templates(ad, templates):
    return dataclasses.replace(ad, templates=templates)


def _capture_warnings():
    from loguru import logger

    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(str(m)), level="WARNING")
    return messages, lambda: logger.remove(sink_id)


def test_job_templates_failure_fails_ad_without_estratega_nor_checkpoint(monkeypatch):
    # D19: a `_JobTemplates.failure` fails the Ad before the Estratega_Adset (Req 4.7).
    deps, job, ad, run_agent, redis, factories, get_tc = _setup(monkeypatch)
    ad = _replace_templates(ad, jrs._JobTemplates((), (), failure="boom cause"))
    with pytest.raises(jrs._AdDiversityFailure) as info:
        _run(deps, ad, job)
    assert "boom cause" in info.value.message
    assert PROJECT_ID in info.value.message and "101" in info.value.message
    assert run_agent.count(ESTRATEGA_ADSET) == 0
    assert factories.count(ESTRATEGA_ADSET) == 0
    assert get_tc.call_count == 0
    assert _strategy_key(101) not in redis.data


def test_job_templates_failure_ignores_existing_checkpoint(monkeypatch):
    # With failed job templates the Template_Order is empty → a stored checkpoint is
    # incoherent, ignored, and the Ad fails without overwriting `strategy` (Req 4.7, 4.8).
    deps, job, ad, run_agent, redis, _, _ = _setup(monkeypatch)
    first, _ = _run(deps, ad, job)
    stored = redis.data[_strategy_key(101)]
    failed = _replace_templates(ad, jrs._JobTemplates((), (), failure="no templates"))
    with pytest.raises(jrs._AdDiversityFailure):
        _run(deps, failed, job)
    assert run_agent.count(ESTRATEGA_ADSET) == 1
    assert redis.data[_strategy_key(101)] == stored
    assert json.loads(stored) == first


def test_incoherent_strategy_checkpoint_is_ignored_with_warning_and_recomputed(monkeypatch):
    # Checkpoint whose Ad_Template != ad_template_for_slot(ad_slot, template_order) (Req 4.8, 4.13).
    from services.adset_diversity import ad_template_for_slot

    deps, job, ad, run_agent, redis, _, _ = _setup(monkeypatch, ad_index=1)
    first, _ = _run(deps, ad, job)
    order = list(ad.templates.template_order)
    expected = ad_template_for_slot(ad.ad_slot, order)
    wrong = next(t for t in order if t != expected)
    stale = json.loads(json.dumps(first))
    for v in stale["variants"]:
        v["template_id"] = wrong
    stale["concept"] = "stale concept"
    redis.data[_strategy_key(102)] = json.dumps(stale)
    run_agent.push(ESTRATEGA_ADSET, [{"index": 0, "concept": "Fresh concept"}])

    messages, stop = _capture_warnings()
    try:
        plan, _ = _run(deps, ad, job)
    finally:
        stop()
    assert any(
        f"[{TASK_ID}]" in m and "incoherent with Template_Order" in m and "ad=102" in m
        for m in messages
    )
    assert run_agent.count(ESTRATEGA_ADSET) == 2
    assert plan["concept"] == "Fresh concept"
    assert [v["template_id"] for v in plan["variants"]] == [expected] * job.n_variants
    assert json.loads(redis.data[_strategy_key(102)]) == plan


def test_coherent_strategy_checkpoint_is_reused(monkeypatch):
    # A checkpoint whose Variant_Slots carry ad_template_for_slot(ad_slot, template_order)
    # and valid Variant_Angles is reused as-is, without Estratega_Adset nor warnings
    # (Req 4.8, 4.13, 14.5).
    from services.adset_diversity import ad_template_for_slot

    deps, job, ad, run_agent, redis, _, get_tc = _setup(monkeypatch, ad_index=1)
    expected = ad_template_for_slot(ad.ad_slot, list(ad.templates.template_order))
    stored = {
        "id": "plan_ad_102", "concept": "Stored concept",
        "variants": expected_slots("plan_ad_102", 1, expected),
        "_project_templates": list(ad.templates.project_templates),
    }
    raw = json.dumps(stored)
    redis.data[_strategy_key(102)] = raw
    run_agent.responses[ESTRATEGA_ADSET] = [AssertionError("must not be called")]

    messages, stop = _capture_warnings()
    try:
        plan, templates = _run(deps, ad, job)
    finally:
        stop()
    assert plan == stored
    assert templates == list(ad.templates.project_templates)
    assert run_agent.count(ESTRATEGA_ADSET) == 0
    assert get_tc.call_count == 0
    assert not any("checkpoint" in m for m in messages)
    assert redis.data[_strategy_key(102)] == raw  # not rewritten


def test_coherent_strategy_checkpoint_without_angles_is_reused_with_recomputed_angles(monkeypatch):
    # Req 14.5 (P14, D22): a coherent checkpoint stored before P14 (slots without `angle`)
    # is reused with assign_variant_angles(plan_id, n) recomputed in code, without
    # Estratega_Adset nor get_template_context, and the corrected plan is stored again.
    from services.adset_diversity import ad_template_for_slot

    deps, job, ad, run_agent, redis, factories, get_tc = _setup(monkeypatch, ad_index=1)
    expected = ad_template_for_slot(ad.ad_slot, list(ad.templates.template_order))
    stored = {
        "id": "plan_ad_102", "concept": "Stored concept",
        "variants": [
            {"variant_key": "plan_ad_102_v1", "template_id": expected},
            {"variant_key": "plan_ad_102_v2", "template_id": expected},
        ],
        "_project_templates": list(ad.templates.project_templates),
    }
    redis.data[_strategy_key(102)] = json.dumps(stored)
    run_agent.responses[ESTRATEGA_ADSET] = [AssertionError("must not be called")]

    messages, stop = _capture_warnings()
    try:
        plan, templates = _run(deps, ad, job)
    finally:
        stop()
    assert plan["variants"] == expected_slots("plan_ad_102", 2, expected)
    assert {k: v for k, v in plan.items() if k != "variants"} == {
        k: v for k, v in stored.items() if k != "variants"
    }
    assert templates == list(ad.templates.project_templates)
    assert run_agent.count(ESTRATEGA_ADSET) == 0
    assert factories.count(ESTRATEGA_ADSET) == 0
    assert get_tc.call_count == 0
    assert any(
        f"[{TASK_ID}]" in m and "ad=102" in m and "without valid Variant_Angles" in m
        for m in messages
    )
    assert json.loads(redis.data[_strategy_key(102)]) == plan


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
