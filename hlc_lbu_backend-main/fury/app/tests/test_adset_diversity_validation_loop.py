"""Unit tests for the validation loop of the Diversity_Path
(`job_runner_service._diversity_validation_loop` / `_regenerate_variants`;
adset-creative-diversity, tasks 11.4, 30.3, 32.2; Req 7.1, 7.2, 7.4–7.10, 7.13,
13.4, D8, D20).

Runs the real functions on top of FakeRedis / FakeRunAgent / FakeAgentFactories:
no network, Redis or LLM.

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_validation_loop.py
"""
import asyncio
import json

import pytest

import services.job_runner_service as jrs
from core.validation import AgentValidationError
from services.adset_diversity import DEFAULT_DECORATIVE_IMAGE_PATTERNS, build_variant_slots
from tests._diversity_pipeline_fakes import (
    COPYWRITER,
    IMAGE_PROMPTER,
    VALIDADOR,
    VALIDADOR_ADSET,
    FakeAgentFactories,
    FakeGetATemplateDefinition,
    FakeRedis,
    FakeRunAgent,
    make_adset_context,
)

TASK_ID = "task-validation-loop"
ID_ADSET = 7
AD_ID = 101
PLAN_ID = f"plan_ad_{AD_ID}"
TEMPLATES = ["tA", "tB"]
FORBIDDEN = ("sibling anchor A",)


def _slots(n):
    return build_variant_slots(PLAN_ID, ad_slot=0, n_variants=n, project_templates=TEMPLATES)


def _copy(slot, headline=None):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "headline": [headline or f"H {slot['variant_key']}"],
        "primary_text": ["P"],
        "description": ["D"],
        "cta": ["LEARN_MORE"],
        "template_elements": [{"element_id": "title", "text": "H"}],
    }


def _prompt(slot, text="x"):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "image_prompts": [{"element_id": "img", "image_prompt": text, "image_request": "y"}],
    }


def _verdict(passed, subset=()):
    return {"overall_pass": passed, "subset_to_regenerate": list(subset)}


class _CtaSpy:
    def __init__(self):
        self.calls = []

    async def __call__(self, copies):
        self.calls.append([c["variant_key"] for c in copies])


class _LogSpy:
    """Replaces `job_runner_service.logger` to inspect the loop's log lines."""

    def __init__(self):
        self.records = []

    def _log(self, level):
        return lambda msg, *a, **k: self.records.append((level, str(msg)))

    def __getattr__(self, level):
        return self._log(level)

    def warnings(self, needle=""):
        return [m for lvl, m in self.records if lvl == "warning" and needle in m]


def _spy_logger(monkeypatch):
    spy = _LogSpy()
    monkeypatch.setattr(jrs, "logger", spy)
    return spy


def _setup(monkeypatch, n_variants, responses):
    ctx = make_adset_context([AD_ID])
    run_agent = FakeRunAgent(responses)
    redis = FakeRedis()
    monkeypatch.setattr(jrs, "_run_agent", run_agent)
    monkeypatch.setattr(jrs, "_redis", lambda: redis)
    factories = FakeAgentFactories()
    ctas = _CtaSpy()
    deps = jrs._DiversityDeps(
        get_template_context=None, delete_variants=None, validate_ctas=ctas,
        save_ads_programmatically=None, generate_images=None, build_abyssale_payload=None,
        post_to_abyssale_and_wait=None, make_estratega_adset_agent=None,
        make_copywriter_agent=factories[COPYWRITER],
        make_image_prompter_agent=factories[IMAGE_PROMPTER],
        make_validador_adset_agent=factories[VALIDADOR_ADSET], progress=lambda *_: None,
        template_definitions=jrs._JobTemplateDefinitions(
            FakeGetATemplateDefinition(), DEFAULT_DECORATIVE_IMAGE_PATTERNS),
    )
    job = jrs._DiversityJob(
        task=None, task_id=TASK_ID, id_adset=ID_ADSET, n_variants=n_variants,
        project_id="test-project-id", id_ad=None, custom_prompt="be bold",
        add_variant=True, id_variant=None, adset_context=ctx,
        adset_context_json=json.dumps(ctx),
    )
    slots = _slots(n_variants)
    ids = tuple(dict.fromkeys(s["template_id"] for s in slots))
    ad = jrs._DiversityAdInput(ad_id=AD_ID, ad_slot=0, territory=None, all_territories=(),
                               forbidden=FORBIDDEN, templates=jrs._JobTemplates(ids, ids))
    plan = {"id": PLAN_ID, "concept": "c", "variants": [dict(s) for s in slots]}
    return deps, job, ad, plan, run_agent, redis, factories, ctas


def _run(deps, ad, job, plan, copies, prompts):
    return asyncio.run(jrs._diversity_validation_loop(
        deps, ad, job, plan, copies, prompts, project_templates=TEMPLATES,
    ))


def _key(step):
    return jrs._cp_key(TASK_ID, AD_ID, step)


def test_single_variant_is_validated_and_approved(monkeypatch):
    slots = _slots(1)
    deps, job, ad, plan, run_agent, _, factories, _ = _setup(
        monkeypatch, 1, {VALIDADOR_ADSET: [_verdict(True)]},
    )
    copies, prompts, report, verdict = _run(deps, ad, job, plan, [_copy(slots[0])], [_prompt(slots[0])])

    assert run_agent.count(VALIDADOR_ADSET) == 1  # also with n_variants == 1 (Req 7.2)
    assert factories.custom_prompts(VALIDADOR_ADSET) == [None]
    assert factories.count(VALIDADOR) == 0
    msg = run_agent.messages_for(VALIDADOR_ADSET)[0]
    assert PLAN_ID in msg and slots[0]["variant_key"] in msg and FORBIDDEN[0] in msg
    # Reduced message (D21): views instead of full proposals, warnings instead of errors.
    assert "Variants:" in msg and "Proposals:" not in msg
    assert "Deterministic diversity warnings" in msg
    assert "Deterministic diversity errors" not in msg
    assert "image_request" not in msg
    assert report["overall_pass"] is True and report["deterministic_pass"] is True
    assert report["iterations"] == 1 and report["ad_failed"] is False
    assert verdict["overall_pass"] is True


def test_semantic_failure_regenerates_only_filtered_subset(monkeypatch):
    slots = _slots(2)
    v1, v2 = slots[0]["variant_key"], slots[1]["variant_key"]
    deps, job, ad, plan, run_agent, redis, _, ctas = _setup(monkeypatch, 2, {
        VALIDADOR_ADSET: [_verdict(False, [PLAN_ID, v2, "plan_1", "unknown"]), _verdict(True)],
        COPYWRITER: [[_copy(slots[1], headline="new headline")]],
        IMAGE_PROMPTER: [[_prompt(slots[1], text="new prompt")]],
    })
    logs = _spy_logger(monkeypatch)
    copies0 = [_copy(s) for s in slots]
    prompts0 = [_prompt(s) for s in slots]
    copies, prompts, report, _ = _run(deps, ad, job, plan, copies0, prompts0)

    assert run_agent.count(VALIDADOR_ADSET) == 2 and run_agent.count(COPYWRITER) == 1
    # Plan ids and foreign values are discarded with a warning naming them (Req 7.13, D8).
    unknown_warnings = logs.warnings("unknown variant_keys")
    assert len(unknown_warnings) == 1
    w = unknown_warnings[0]
    assert f"[{TASK_ID}]" in w and f"ad={AD_ID}" in w
    assert all(repr(v) in w for v in (PLAN_ID, "plan_1", "unknown")) and repr(v2) not in w
    # Only v2 is sent to the agents (D9) and regenerated; v1 unchanged (Req 7.4).
    copy_msg = run_agent.messages_for(COPYWRITER)[0]
    assert v2 in copy_msg and v1 not in copy_msg.split("Variant_Slots:")[1].split("\n")[0]
    assert copies[0] == copies0[0] and copies[1]["headline"] == ["new headline"]
    assert prompts[0] == prompts0[0] and prompts[1]["image_prompts"][0]["image_prompt"] == "new prompt"
    assert [c["template_id"] for c in copies] == [s["template_id"] for s in slots]
    assert ctas.calls == [[v2]]
    # Checkpoints updated after the regeneration (Req 7.5).
    assert json.loads(redis.data[_key("copy")]) == copies
    assert json.loads(redis.data[_key("image_prompts")]) == prompts
    assert report["overall_pass"] is True and report["iterations"] == 2


@pytest.mark.parametrize("subset", [[], ["unknown_key"]])
def test_empty_subset_stops_with_overall_pass_false(monkeypatch, subset):
    slots = _slots(2)
    deps, job, ad, plan, run_agent, _, _, _ = _setup(
        monkeypatch, 2, {VALIDADOR_ADSET: [_verdict(False, subset)]},
    )
    _, _, report, _ = _run(deps, ad, job, plan, [_copy(s) for s in slots], [_prompt(s) for s in slots])

    assert run_agent.count(VALIDADOR_ADSET) == 1 and run_agent.count(COPYWRITER) == 0
    assert report["overall_pass"] is False and report["deterministic_pass"] is True
    assert report["iterations"] == 1 and report["subset_to_regenerate"] == []


def test_subset_with_only_plan_ids_does_not_regenerate(monkeypatch):
    slots = _slots(2)
    deps, job, ad, plan, run_agent, redis, _, ctas = _setup(
        monkeypatch, 2, {VALIDADOR_ADSET: [_verdict(False, [PLAN_ID, "plan_1"])]},
    )
    logs = _spy_logger(monkeypatch)
    copies0 = [_copy(s) for s in slots]
    prompts0 = [_prompt(s) for s in slots]
    copies, prompts, report, verdict = _run(deps, ad, job, plan, copies0, prompts0)

    # Filtered subset is empty → treated as an empty subset (Req 7.7, 7.13, D8).
    assert run_agent.count(VALIDADOR_ADSET) == 1
    assert run_agent.count(COPYWRITER) == 0 and run_agent.count(IMAGE_PROMPTER) == 0
    assert ctas.calls == [] and _key("copy") not in redis.data
    assert copies == copies0 and prompts == prompts0
    assert report["overall_pass"] is False and report["deterministic_pass"] is True
    assert report["ad_failed"] is False and report["iterations"] == 1
    assert report["subset_to_regenerate"] == []
    assert verdict["overall_pass"] is False
    discarded = logs.warnings("unknown variant_keys")
    assert len(discarded) == 1 and f"[{TASK_ID}]" in discarded[0] and f"ad={AD_ID}" in discarded[0]
    assert repr(PLAN_ID) in discarded[0] and repr("plan_1") in discarded[0]
    not_approved = logs.warnings("did not approve")
    assert len(not_approved) == 1 and f"[{TASK_ID}]" in not_approved[0]
    assert f"ad={AD_ID}" in not_approved[0]


def test_extra_verdict_keys_are_ignored(monkeypatch):
    slots = _slots(2)
    v1, v2 = slots[0]["variant_key"], slots[1]["variant_key"]
    first = {
        "overall_pass": False, "subset_to_regenerate": [v1],
        "justification": f"regenerate {v2} too", "issues": [{"variant_key": v2}],
        "variants_to_fix": [v2], "regenerate_all": True,
    }
    second = {"overall_pass": True, "subset_to_regenerate": [v2], "reason": "fine"}
    deps, job, ad, plan, run_agent, _, _, ctas = _setup(monkeypatch, 2, {
        VALIDADOR_ADSET: [first, second],
        COPYWRITER: [[_copy(slots[0], headline="new")]],
        IMAGE_PROMPTER: [[_prompt(slots[0])]],
    })
    copies0 = [_copy(s) for s in slots]
    copies, _, report, verdict = _run(deps, ad, job, plan, copies0, [_prompt(s) for s in slots])

    # Only overall_pass and subset_to_regenerate drive the loop (Req 13.4).
    assert ctas.calls == [[v1]] and run_agent.count(COPYWRITER) == 1
    assert copies[0]["headline"] == ["new"] and copies[1] == copies0[1]
    # overall_pass=True wins even with a non-empty subset; nothing else is regenerated.
    assert run_agent.count(VALIDADOR_ADSET) == 2
    assert report["overall_pass"] is True and report["iterations"] == 2
    assert report["subset_to_regenerate"] == [v2]
    assert verdict["overall_pass"] is True


def test_total_iterations_capped_at_three_mixing_checker_and_validador(monkeypatch):
    slots = _slots(2)
    v1, v2 = slots[0]["variant_key"], slots[1]["variant_key"]
    dup = [_copy(s, headline="same") for s in slots]
    deps, job, ad, plan, run_agent, _, factories, _ = _setup(monkeypatch, 2, {
        # Round 1 (checker errors) fixes the duplicates; then Validador rejects twice.
        COPYWRITER: [[_copy(slots[0], headline="a"), _copy(slots[1], headline="b")],
                     [_copy(slots[1], headline="c")]],
        IMAGE_PROMPTER: [[_prompt(s) for s in slots], [_prompt(slots[1])]],
        VALIDADOR_ADSET: [_verdict(False, [v2])] * 2,
        # A 4th iteration would need more scripted responses (strict FakeRunAgent).
    })
    _, _, report, _ = _run(deps, ad, job, plan, dup, [_prompt(s) for s in slots])

    assert report["iterations"] == 3 and report["overall_pass"] is False
    assert report["subset_to_regenerate"] == [v2]
    # Iteration 1 without Validador; iterations 2–3 with it; 2 regeneration rounds at most.
    assert [c.user_id.rsplit("_", 1)[-1] for c in run_agent.calls
            if c.agent_name == VALIDADOR_ADSET] == ["2", "3"]
    assert run_agent.count(COPYWRITER) == 2 and factories.count(VALIDADOR_ADSET) == 1
    assert v1 not in run_agent.messages_for(COPYWRITER)[1].split("Variant_Slots:")[1].split("\n")[0]


def test_persistent_semantic_failure_continues_after_three_iterations(monkeypatch):
    slots = _slots(2)
    v1 = slots[0]["variant_key"]
    deps, job, ad, plan, run_agent, _, factories, _ = _setup(monkeypatch, 2, {
        VALIDADOR_ADSET: [_verdict(False, [v1])] * 3,
        COPYWRITER: [[_copy(slots[0], headline=f"H{i}")] for i in range(2)],
        IMAGE_PROMPTER: [[_prompt(slots[0])]] * 2,
    })
    _, _, report, _ = _run(deps, ad, job, plan, [_copy(s) for s in slots], [_prompt(s) for s in slots])

    assert run_agent.count(VALIDADOR_ADSET) == 3 and run_agent.count(COPYWRITER) == 2
    # Created lazily once per Ad and reused across the 3 calls (D20, Req 8.6).
    assert factories.count(VALIDADOR_ADSET) == 1
    assert factories.custom_prompts(VALIDADOR_ADSET) == [None]
    agents = {id(c.agent) for c in run_agent.calls if c.agent_name == VALIDADOR_ADSET}
    assert len(agents) == 1
    assert report["overall_pass"] is False and report["iterations"] == 3
    assert report["subset_to_regenerate"] == [v1]


def test_validador_error_on_intermediate_iteration_retries_without_regenerating(monkeypatch):
    slots = _slots(2)
    deps, job, ad, plan, run_agent, _, factories, _ = _setup(monkeypatch, 2, {
        VALIDADOR_ADSET: [{"overall_pass": "yes"}, _verdict(True)],
    })
    _, _, report, _ = _run(deps, ad, job, plan, [_copy(s) for s in slots], [_prompt(s) for s in slots])

    assert run_agent.count(VALIDADOR_ADSET) == 2 and run_agent.count(COPYWRITER) == 0
    assert factories.count(VALIDADOR_ADSET) == 1  # not re-created after an execution error
    assert report["overall_pass"] is True and report["iterations"] == 2


def test_validador_error_on_last_iteration_is_reraised(monkeypatch):
    slots = _slots(2)
    deps, job, ad, plan, run_agent, _, _, _ = _setup(monkeypatch, 2, {
        VALIDADOR_ADSET: [{"subset_to_regenerate": []}] * 3,
    })
    with pytest.raises(AgentValidationError):
        _run(deps, ad, job, plan, [_copy(s) for s in slots], [_prompt(s) for s in slots])
    assert run_agent.count(VALIDADOR_ADSET) == 3


def test_persistent_duplicate_copies_fail_the_ad(monkeypatch):
    slots = _slots(2)
    dup = [_copy(s, headline="same") for s in slots]
    deps, job, ad, plan, run_agent, _, factories, _ = _setup(monkeypatch, 2, {
        COPYWRITER: [[_copy(s, headline="same") for s in slots]] * 2,
        IMAGE_PROMPTER: [[_prompt(s) for s in slots]] * 2,
    })
    with pytest.raises(jrs._AdDiversityFailure) as exc_info:
        _run(deps, ad, job, plan, dup, [_prompt(s) for s in slots])

    # Checker errors in every iteration: the Validador_Adset is never created nor
    # invoked (Req 7.2, D20); both variant_keys of the duplicate pair are regenerated
    # in each non-final round (D7).
    assert run_agent.count(VALIDADOR_ADSET) == 0 and factories.count(VALIDADOR_ADSET) == 0
    assert run_agent.count(COPYWRITER) == 2
    failure = exc_info.value
    assert failure.iterations == 3 and failure.deterministic_errors
    assert "repeat the first headline" in failure.deterministic_errors[0]


def test_checker_errors_skip_validador_and_regenerate_only_checker_keys(monkeypatch):
    slots = _slots(3)
    v1, v2, v3 = (s["variant_key"] for s in slots)
    copies0 = [_copy(slots[0], headline="same"), _copy(slots[1], headline="same"), _copy(slots[2])]
    deps, job, ad, plan, run_agent, _, factories, _ = _setup(monkeypatch, 3, {
        COPYWRITER: [[_copy(slots[0], headline="fresh 1"), _copy(slots[1], headline="fresh 2")]],
        IMAGE_PROMPTER: [[_prompt(slots[0]), _prompt(slots[1])]],
        VALIDADOR_ADSET: [_verdict(True)],
    })
    copies, _, report, verdict = _run(deps, ad, job, plan, copies0, [_prompt(s) for s in slots])

    # Iteration 1: checker errors → no Validador_Adset, only the checker's keys (Req 7.2, 7.4).
    copy_slots = run_agent.messages_for(COPYWRITER)[0].split("Variant_Slots:")[1].split("\n")[0]
    assert v1 in copy_slots and v2 in copy_slots and v3 not in copy_slots
    assert copies[2] == copies0[2]
    # Iteration 2: checker clean → a single Validador_Adset call (created once).
    assert run_agent.count(VALIDADOR_ADSET) == 1 and factories.count(VALIDADOR_ADSET) == 1
    assert run_agent.calls[-1].user_id.endswith("_div_val_2")
    assert report["iterations"] == 2 and report["overall_pass"] is True
    assert verdict["overall_pass"] is True


def test_regeneration_failure_keeps_previous_and_continues(monkeypatch):
    slots = _slots(2)
    v2 = slots[1]["variant_key"]
    deps, job, ad, plan, run_agent, redis, _, _ = _setup(monkeypatch, 2, {
        VALIDADOR_ADSET: [_verdict(False, [v2]), _verdict(True)],
        COPYWRITER: [[]],  # invalid shape → AgentValidationError (Req 7.10)
    })
    copies0 = [_copy(s) for s in slots]
    prompts0 = [_prompt(s) for s in slots]
    copies, prompts, report, _ = _run(deps, ad, job, plan, copies0, prompts0)

    assert copies == copies0 and prompts == prompts0
    assert run_agent.count(IMAGE_PROMPTER) == 0
    assert _key("copy") not in redis.data
    assert report["overall_pass"] is True and report["iterations"] == 2


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
