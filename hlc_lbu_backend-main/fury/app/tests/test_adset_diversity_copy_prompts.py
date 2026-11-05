"""Unit tests for the initial copywriting and image prompts of the Diversity_Path
(`job_runner_service._load_or_generate_copies_and_prompts`; adset-creative-diversity,
task 11.3; Req 5.1–5.8, 8.6).

Runs the real functions on top of FakeRedis / FakeRunAgent / FakeAgentFactories:
no network, Redis or LLM.

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_copy_prompts.py
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
    FakeAgentFactories,
    FakeGetATemplateDefinition,
    FakeRedis,
    FakeRunAgent,
    make_adset_context,
)

TASK_ID = "task-copy-prompts"
ID_ADSET = 7
AD_ID = 101
PLAN_ID = f"plan_ad_{AD_ID}"
CUSTOM_PROMPT = "be bold"
FORBIDDEN = ("sibling anchor A", "sibling anchor B")
CATALOG = ["LEARN_MORE", "SHOP_NOW"]
SLOTS = build_variant_slots(PLAN_ID, ad_slot=0, n_variants=2, project_templates=["tA", "tB"])


def _copy(slot, cta=("LEARN_MORE",)):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "headline": [f"H {slot['variant_key']}"],
        "primary_text": ["P"],
        "description": ["D"],
        "cta": list(cta),
        "template_elements": [{"element_id": "title", "text": "H"}],
    }


def _prompt(slot):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "image_prompts": [{"element_id": "img", "image_prompt": "x", "image_request": "y"}],
    }


def _plan():
    return {"id": PLAN_ID, "concept": "c", "variants": [dict(s) for s in SLOTS]}


class _CtaSpy:
    """Same filtering as the `_validate_ctas` closure, recording each call."""

    def __init__(self):
        self.calls: list[list[dict]] = []

    async def __call__(self, copies):
        self.calls.append(copies)
        for c in copies:
            c["cta"] = [v for v in c.get("cta", []) or [] if v in CATALOG]


def _templates():
    ids = tuple(dict.fromkeys(s["template_id"] for s in SLOTS))
    return jrs._JobTemplates(ids, ids)


def _setup(monkeypatch, *, responses=None, redis=None):
    ctx = make_adset_context([AD_ID])
    run_agent = FakeRunAgent(responses or {})
    redis = redis or FakeRedis()
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
        make_validador_adset_agent=None, progress=lambda *_: None,
        template_definitions=jrs._JobTemplateDefinitions(
            FakeGetATemplateDefinition(), DEFAULT_DECORATIVE_IMAGE_PATTERNS),
    )
    job = jrs._DiversityJob(
        task=None, task_id=TASK_ID, id_adset=ID_ADSET, n_variants=len(SLOTS),
        project_id="test-project-id", id_ad=None, custom_prompt=CUSTOM_PROMPT,
        add_variant=True, id_variant=None, adset_context=ctx,
        adset_context_json=json.dumps(ctx),
    )
    ad = jrs._DiversityAdInput(
        ad_id=AD_ID, ad_slot=0, territory=None, all_territories=(), forbidden=FORBIDDEN,
        templates=_templates(),
    )
    return deps, job, ad, run_agent, redis, factories, ctas


def _run(deps, ad, job):
    return asyncio.run(jrs._load_or_generate_copies_and_prompts(deps, ad, job, _plan()))


def _key(step):
    return jrs._cp_key(TASK_ID, AD_ID, step)


def test_generates_copies_and_prompts_once_and_stores_checkpoints(monkeypatch):
    copies = [_copy(SLOTS[0], cta=("LEARN_MORE", "NOT_IN_CATALOG")), _copy(SLOTS[1])]
    prompts = [_prompt(s) for s in SLOTS]
    deps, job, ad, run_agent, redis, factories, ctas = _setup(
        monkeypatch, responses={COPYWRITER: [copies], IMAGE_PROMPTER: [prompts]},
    )
    out_copies, out_prompts = _run(deps, ad, job)

    assert run_agent.count(COPYWRITER) == 1 and run_agent.count(IMAGE_PROMPTER) == 1
    assert [c["variant_key"] for c in out_copies] == [s["variant_key"] for s in SLOTS]
    assert out_prompts == prompts
    # CTAs filtered against the catalog (Req 5.4).
    assert len(ctas.calls) == 1
    assert out_copies[0]["cta"] == ["LEARN_MORE"]
    # custom_prompt to both factories (Req 8.6).
    assert factories.custom_prompts(COPYWRITER) == [CUSTOM_PROMPT]
    assert factories.custom_prompts(IMAGE_PROMPTER) == [CUSTOM_PROMPT]
    # Messages carry Variant_Slots, Forbidden_Territories and the context (Req 5.1, 5.7, 2.5).
    copy_msg = run_agent.messages_for(COPYWRITER)[0]
    assert all(f in copy_msg for f in FORBIDDEN)
    assert all(s["variant_key"] in copy_msg for s in SLOTS)
    assert "FULL ADSET CONTEXT" in copy_msg
    img_msg = run_agent.messages_for(IMAGE_PROMPTER)[0]
    assert "FULL ADSET CONTEXT" in img_msg and "Copies:" in img_msg
    # Checkpoints stored (Req 5.6, 5.7).
    assert len(json.loads(redis.data[_key("copy")])) == 2
    assert json.loads(redis.data[_key("image_prompts")]) == prompts


def test_checkpoints_reused_and_ctas_still_validated(monkeypatch):
    redis = FakeRedis({
        _key("copy"): [_copy(SLOTS[0], cta=("BAD",)), _copy(SLOTS[1])],
        _key("image_prompts"): [_prompt(s) for s in SLOTS],
    })
    deps, job, ad, run_agent, _, factories, ctas = _setup(monkeypatch, redis=redis)
    copies, prompts = _run(deps, ad, job)

    assert run_agent.call_count == 0
    assert len(ctas.calls) == 1
    assert copies[0]["cta"] == []
    assert len(prompts) == 2


def test_foreign_copy_checkpoint_is_regenerated(monkeypatch):
    # Legacy-shaped checkpoint (no variant_key): ignored and regenerated.
    redis = FakeRedis({_key("copy"): [{"plan_id": "plan_1", "headline": ["x"]}]})
    deps, job, ad, run_agent, _, _, _ = _setup(
        monkeypatch, redis=redis,
        responses={COPYWRITER: [[_copy(s) for s in SLOTS]],
                   IMAGE_PROMPTER: [[_prompt(s) for s in SLOTS]]},
    )
    copies, _ = _run(deps, ad, job)
    assert run_agent.count(COPYWRITER) == 1
    assert len(copies) == 2


@pytest.mark.parametrize("bad", [
    [],
    [_copy(SLOTS[0])],                                     # one copy for two slots
    [_copy(SLOTS[0]), _copy(SLOTS[0])],                    # repeated variant_key
    # template_id differs from its Variant_Slot (P11: every slot of the Ad uses "tA").
    [_copy(SLOTS[0]), {**_copy(SLOTS[1]), "template_id": "tB"}],
])
def test_invalid_copy_raises_without_checkpoint(monkeypatch, bad):
    # The same invalid answer on every attempt (initial call + bounded retry).
    deps, job, ad, run_agent, redis, _, ctas = _setup(
        monkeypatch, responses={COPYWRITER: [bad] * jrs._DIVERSITY_AGENT_ATTEMPTS})
    with pytest.raises(AgentValidationError) as info:
        _run(deps, ad, job)
    retryable = info.value.code in jrs._RETRYABLE_AGENT_CODES
    assert run_agent.count(COPYWRITER) == (jrs._DIVERSITY_AGENT_ATTEMPTS if retryable else 1)
    assert run_agent.count(IMAGE_PROMPTER) == 0
    assert _key("copy") not in redis.data
    assert ctas.calls == []


def test_invalid_image_prompts_raise_without_checkpoint(monkeypatch):
    bad = [_prompt(SLOTS[0]), {**_prompt(SLOTS[1]), "plan_id": "plan_ad_999"}]
    deps, job, ad, run_agent, redis, _, _ = _setup(
        monkeypatch, responses={COPYWRITER: [[_copy(s) for s in SLOTS]],
                                IMAGE_PROMPTER: [bad] * jrs._DIVERSITY_AGENT_ATTEMPTS},
    )
    with pytest.raises(AgentValidationError):
        _run(deps, ad, job)
    assert run_agent.count(IMAGE_PROMPTER) == jrs._DIVERSITY_AGENT_ATTEMPTS
    assert _key("copy") in redis.data
    assert _key("image_prompts") not in redis.data


# ---------------------------------------------------------------------------
# Production regressions (job 0930d359, adset 355)
# ---------------------------------------------------------------------------

def _without_key(item, plan_id=None):
    out = {k: v for k, v in item.items() if k != "variant_key"}
    if plan_id is not None:
        out["plan_id"] = plan_id
    return out


@pytest.mark.parametrize("shape", ["variant_key_in_plan_id", "variant_key_missing"])
def test_copy_without_variant_key_is_repaired(monkeypatch, shape):
    """ad=827: the Copywriter followed the Legacy schema (no `variant_key`), first writing
    the variant_key into `plan_id`, then omitting it. The response is repaired, not
    rejected, and the agent is called once."""
    copies = [
        _without_key(_copy(s), s["variant_key"] if shape == "variant_key_in_plan_id" else None)
        for s in SLOTS
    ]
    deps, job, ad, run_agent, redis, _, _ = _setup(
        monkeypatch, responses={COPYWRITER: [copies], IMAGE_PROMPTER: [[_prompt(s) for s in SLOTS]]},
    )
    out, _ = _run(deps, ad, job)

    assert run_agent.count(COPYWRITER) == 1
    assert [(c["plan_id"], c["variant_key"], c["template_id"]) for c in out] == [
        (PLAN_ID, s["variant_key"], s["template_id"]) for s in SLOTS
    ]
    stored = json.loads(redis.data[_key("copy")])
    assert [c["variant_key"] for c in stored] == [s["variant_key"] for s in SLOTS]


def test_empty_image_prompter_answer_is_retried(monkeypatch):
    """ad=828: Image_Prompter returned an empty answer (tokens_out=0). One retry with the
    rejection reason; the valid second answer is stored."""
    prompts = [_prompt(s) for s in SLOTS]
    deps, job, ad, run_agent, redis, _, _ = _setup(
        monkeypatch,
        responses={COPYWRITER: [[_copy(s) for s in SLOTS]], IMAGE_PROMPTER: ["", prompts]},
    )
    _, out = _run(deps, ad, job)

    assert run_agent.count(IMAGE_PROMPTER) == 2
    assert out == prompts
    first, retry = run_agent.messages_for(IMAGE_PROMPTER)
    assert "REJECTED" not in first
    assert retry.startswith(first) and "Empty response from agent" in retry
    assert json.loads(redis.data[_key("image_prompts")]) == prompts


def test_messages_carry_identity_contract_and_no_plan_variants(monkeypatch):
    """The plan is sent without its `variants` (they only travel as Variant_Slots), and the
    message spells out the plan_id / variant_key / template_id identity."""
    deps, job, ad, run_agent, _, _, _ = _setup(
        monkeypatch, responses={COPYWRITER: [[_copy(s) for s in SLOTS]],
                                IMAGE_PROMPTER: [[_prompt(s) for s in SLOTS]]},
    )
    _run(deps, ad, job)
    for msg in (run_agent.messages_for(COPYWRITER)[0], run_agent.messages_for(IMAGE_PROMPTER)[0]):
        assert "OUTPUT IDENTITY" in msg and "NEVER put a variant_key in plan_id" in msg
        plan_line = next(l for l in msg.splitlines() if l.startswith("Plan: "))
        assert '"variants"' not in plan_line


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
