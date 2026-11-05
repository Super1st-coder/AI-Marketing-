"""Property-based tests for the Diversity_Path orchestration in
`services.job_runner_service` (adset-creative-diversity, tasks 11.6–11.10).

Everything runs in memory on top of the shared fakes (FakeRedis / FakeRunAgent /
FakeAgentFactories): no network, Redis or LLM. Module attributes are patched and
restored per Hypothesis example (`_patched`), never with pytest's `monkeypatch`.

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_pipeline_properties.py
"""
import asyncio
import contextlib
import copy
import json
from dataclasses import dataclass, field

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import services.diversity_checker as diversity_checker
import services.job_runner_service as jrs
from core.validation import AgentValidationError
from services.adset_diversity import DEFAULT_DECORATIVE_IMAGE_PATTERNS, build_variant_slots
from services.diversity_checker import DiversityCheckResult, DiversityIssue
from tests._diversity_pipeline_fakes import (
    COPYWRITER,
    IMAGE_PROMPTER,
    VALIDADOR,
    VALIDADOR_ADSET,
    FakeAgentFactories,
    FakeGetATemplateDefinition,
    FakeRedis,
    FakeRunAgent,
    conformant_image_prompts,
    image_elements_from_message,
    make_adset_context,
)

# ---------------------------------------------------------------------------
# Shared constants, builders and harness (reused by Properties 13, 16, 17, 18, 23)
# ---------------------------------------------------------------------------

TASK_ID = "task-diversity-properties"
ID_ADSET = 7
AD_ID = 101
PLAN_ID = f"plan_ad_{AD_ID}"
TEMPLATES = ["tA", "tB", "tC"]
FORBIDDEN = ("sibling anchor A",)
MAX_ITERATIONS = jrs._DIVERSITY_MAX_RETRIES  # 3 (Req 7.5)


@contextlib.contextmanager
def _patched(*targets):
    """Set `(obj, attr, value)` for the duration of one example, then restore."""
    saved = [(obj, attr, getattr(obj, attr)) for obj, attr, _ in targets]
    try:
        for obj, attr, value in targets:
            setattr(obj, attr, value)
        yield
    finally:
        for obj, attr, value in reversed(saved):
            setattr(obj, attr, value)


def _slots(n_variants):
    return build_variant_slots(PLAN_ID, ad_slot=0, n_variants=n_variants,
                               project_templates=TEMPLATES)


def _plan(n_variants):
    return {"id": PLAN_ID, "concept": "c", "variants": [dict(s) for s in _slots(n_variants)]}


def _copy(slot, headline):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "headline": [headline],
        "primary_text": ["P"],
        "description": ["D"],
        "cta": ["LEARN_MORE"],
        "template_elements": [{"element_id": "title", "text": headline}],
    }


def _prompt(slot, text):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "image_prompts": [{"element_id": "img", "image_prompt": text, "image_request": "y"}],
    }


class _CtaSpy:
    """`deps.validate_ctas` stand-in recording the variant_keys it receives."""

    def __init__(self):
        self.calls = []

    async def __call__(self, copies):
        self.calls.append([c["variant_key"] for c in copies])


@dataclass
class _Harness:
    deps: object
    job: object
    ad: object
    run_agent: FakeRunAgent
    redis: FakeRedis
    factories: FakeAgentFactories
    ctas: _CtaSpy
    events: list = field(default_factory=list)


def _make_harness(n_variants, run_agent, **deps_overrides):
    ctx = make_adset_context([AD_ID])
    factories = FakeAgentFactories()
    ctas = _CtaSpy()
    deps_kwargs = dict(
        get_template_context=None, delete_variants=None, validate_ctas=ctas,
        save_ads_programmatically=None, generate_images=None, build_abyssale_payload=None,
        post_to_abyssale_and_wait=None, make_estratega_adset_agent=None,
        make_copywriter_agent=factories[COPYWRITER],
        make_image_prompter_agent=factories[IMAGE_PROMPTER],
        make_validador_adset_agent=factories[VALIDADOR_ADSET], progress=lambda *_: None,
        template_definitions=jrs._JobTemplateDefinitions(
            FakeGetATemplateDefinition(), DEFAULT_DECORATIVE_IMAGE_PATTERNS),
    )
    deps_kwargs.update(deps_overrides)
    deps = jrs._DiversityDeps(**deps_kwargs)
    job = jrs._DiversityJob(
        task=None, task_id=TASK_ID, id_adset=ID_ADSET, n_variants=n_variants,
        project_id="test-project-id", id_ad=None, custom_prompt=None,
        add_variant=True, id_variant=None, adset_context=ctx,
        adset_context_json=json.dumps(ctx),
    )
    ids = tuple(dict.fromkeys(s["template_id"] for s in _slots(n_variants)))
    ad = jrs._DiversityAdInput(ad_id=AD_ID, ad_slot=0, territory=None, all_territories=(),
                               forbidden=FORBIDDEN, templates=jrs._JobTemplates(ids, ids))
    return _Harness(deps=deps, job=job, ad=ad, run_agent=run_agent, redis=FakeRedis(),
                    factories=factories, ctas=ctas)


def _cp_key(step):
    return jrs._cp_key(TASK_ID, AD_ID, step)


def _load_cp(redis, step):
    raw = redis.data.get(_cp_key(step))
    return None if raw is None else json.loads(raw)


# ---------------------------------------------------------------------------
# Property 13 — scripts and reference model
# ---------------------------------------------------------------------------

UNKNOWN_KEYS = ("unknown_key", "plan_1", "plan_ad_999_v1", "")
# Extra verdict keys the loop must ignore (Req 13.4): misleading names (approval flags,
# alternative subsets, angle / template rewrites) that a careless reader might honour.
EXTRA_VERDICT_KEYS = ("issues", "regenerate_all", "variants_to_regenerate", "subset",
                      "approved", "Overall_Pass", "angle", "angles", "new_angles",
                      "template_id", "variants", "notes")


def _extra_verdict_values(keys):
    return st.one_of(
        st.booleans(),
        st.none(),
        st.text(alphabet="abcxyz_ ", max_size=8),
        st.lists(st.sampled_from(keys + list(UNKNOWN_KEYS)), max_size=4),
        st.dictionaries(st.sampled_from(keys), st.text(alphabet="abcxyz_", max_size=6),
                        max_size=len(keys)),
    )


@st.composite
def validation_scripts(draw):
    """`(n_variants, det_keys[3], validador[3], regen[2])`.

    - det_keys[i]: variant_keys with deterministic errors in iteration i+1.
    - validador[i]: ("error",) → AgentValidationError, or
      ("verdict", overall_pass, subset_to_regenerate with valid/unknown keys,
      extra keys to ignore — Req 13.4).
    - regen[r]: "ok" | "copy_error" | "prompt_error" for regeneration round r+1.
    """
    n_variants = draw(st.integers(1, 4))
    keys = [s["variant_key"] for s in _slots(n_variants)]
    det = draw(st.lists(st.frozensets(st.sampled_from(keys)), min_size=3, max_size=3))
    verdict = st.tuples(
        st.just("verdict"),
        st.booleans(),
        st.lists(st.sampled_from(keys + list(UNKNOWN_KEYS)), max_size=5),
        st.dictionaries(st.sampled_from(EXTRA_VERDICT_KEYS), _extra_verdict_values(keys),
                        max_size=4),
    )
    validador = draw(st.lists(st.one_of(st.just(("error",)), verdict), min_size=3, max_size=3))
    regen = draw(st.lists(st.sampled_from(["ok", "copy_error", "prompt_error"]),
                          min_size=2, max_size=2))
    return n_variants, det, validador, regen


def _model(slot_keys, det, validador, regen):
    """Reference semantics of Req 7.1, 7.2, 7.4–7.10 with the Validador_Adset (D20).

    Each iteration runs the checker first. With checker errors the Validador_Adset is
    NOT invoked (Req 7.2): non-final → regenerate exactly the checker keys; final → the
    Ad fails (Req 7.6). Without errors the Validador_Adset step of that iteration is
    consumed; a non-final, non-approved verdict with a non-empty filtered subset (D8)
    regenerates exactly that subset (D20). Never the union of both sets.

    Returns the expected iterations, the iterations where the Validador_Adset is invoked,
    regeneration rounds `[(iteration, keys_in_slot_order, outcome, source)]` with source
    'checker' | 'validador', outcome ('approved' | 'semantic_fail' | 'det_fail' |
    'raise'), the last filtered subset and overall_pass."""
    rounds, subset, validador_pass = [], [], False
    validador_iterations = []
    iteration, outcome = 0, None
    while iteration < MAX_ITERATIONS:
        iteration += 1
        last = iteration == MAX_ITERATIONS
        det_keys = set(det[iteration - 1])
        if det_keys:  # Req 7.2 — no Validador_Adset call
            if last:
                outcome = "det_fail"  # Req 7.6
                break
            rounds.append((iteration, [k for k in slot_keys if k in det_keys],
                           regen[len(rounds)], "checker"))
            continue
        validador_iterations.append(iteration)
        step = validador[iteration - 1]
        if step[0] == "error":
            if last:
                outcome = "raise"  # Req 7.9
                break
            continue  # Req 7.8 — no regeneration
        _, validador_pass, raw_subset, _extra = step  # extra keys ignored (Req 13.4)
        subset = [k for k in slot_keys if k in raw_subset]  # D8
        if validador_pass:
            outcome = "approved"
            break
        if not subset or last:
            outcome = "semantic_fail"  # Req 7.7
            break
        rounds.append((iteration, list(subset), regen[len(rounds)], "validador"))
    assert outcome is not None  # every path to the last iteration breaks
    return {"iterations": iteration, "validador_iterations": validador_iterations,
            "rounds": rounds, "outcome": outcome, "subset": subset,
            "overall_pass": validador_pass}


# Feature: adset-creative-diversity, Property 13: Bucle de validación acotado y regeneración selectiva
@settings(max_examples=100, deadline=None)
@given(script=validation_scripts())
def test_property_13_bounded_validation_loop_and_selective_regeneration(script):
    """**Validates: Requirements 7.1, 7.2, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 8.6, 13.2, 13.4**"""
    n_variants, det, validador, regen = script
    slots = _slots(n_variants)
    slot_by_key = {s["variant_key"]: s for s in slots}
    slot_keys = list(slot_by_key)
    angles_before = {s["variant_key"]: s["angle"] for s in slots}
    plan = _plan(n_variants)
    plan_before = copy.deepcopy(plan)
    expected = _model(slot_keys, det, validador, regen)

    copies0 = [_copy(s, f"H0-{s['variant_key']}") for s in slots]
    prompts0 = [_prompt(s, f"P0-{s['variant_key']}") for s in slots]

    # Expected state after each round (only successful rounds change it, Req 7.10)
    # and the Checkpoint visible at the start of every iteration (None = absent).
    exp_copies = {c["variant_key"]: c for c in copy.deepcopy(copies0)}
    exp_prompts = {p["variant_key"]: p for p in copy.deepcopy(prompts0)}
    checkpoint_at = {}
    checkpoint = None
    for it in range(1, expected["iterations"] + 1):
        checkpoint_at[it] = checkpoint
        for r, (round_it, keys, outcome, _) in enumerate(expected["rounds"], start=1):
            if round_it == it and outcome == "ok":
                for k in keys:
                    exp_copies[k] = _copy(slot_by_key[k], f"R{r}-{k}")
                    exp_prompts[k] = _prompt(slot_by_key[k], f"PR{r}-{k}")
                checkpoint = ([exp_copies[k] for k in slot_keys],
                              [exp_prompts[k] for k in slot_keys])
    # Rounds that reach the Image_Prompter (the Copywriter succeeded), 1-based numbers.
    prompter_rounds = [(r, keys, outcome) for r, (_, keys, outcome, _)
                       in enumerate(expected["rounds"], start=1) if outcome != "copy_error"]

    events = []
    last_verdict = {"value": {}}  # last valid verdict sent (returned as-is by the loop)
    redis_holder = {}
    copy_round = {"n": 0}
    prompt_round = {"n": 0}

    def fake_check_variants(plan_arg, copies_arg, prompts_arg, **kwargs):
        i = sum(1 for e in events if e[0] == "checker")
        events.append(("checker", i + 1))
        redis = redis_holder["redis"]
        # Req 7.5 — Checkpoints reflect the state after each successful regeneration.
        cp = checkpoint_at[i + 1]
        if cp is None:
            assert _load_cp(redis, "copy") is None and _load_cp(redis, "image_prompts") is None
        else:
            assert _load_cp(redis, "copy") == cp[0]
            assert _load_cp(redis, "image_prompts") == cp[1]
        assert list(copies_arg) == (cp[0] if cp else copies0)
        assert list(prompts_arg) == (cp[1] if cp else prompts0)
        assert kwargs.get("n_variants") == n_variants
        errors = tuple(
            DiversityIssue(code="COPY_REPEATED", message=f"scripted error {k}", variant_keys=(k,))
            for k in slot_keys if k in det[i]
        )
        return DiversityCheckResult(errors=errors)

    def validador_response(call):
        # Req 7.1 — the checker of this same iteration ran right before this call.
        assert events and events[-1][0] == "checker"
        it = events[-1][1]
        # Req 7.2 — the Validador_Adset is only invoked when the checker found no errors.
        assert not det[it - 1]
        events.append(("validador", it))
        step = validador[it - 1]
        if step[0] == "error":
            return {"overall_pass": "not-a-bool"}  # → AgentValidationError
        # Req 13.4 — extra keys travel with the verdict and must be ignored.
        verdict = {**copy.deepcopy(step[3]),
                   "overall_pass": step[1], "subset_to_regenerate": list(step[2])}
        last_verdict["value"] = copy.deepcopy(verdict)
        return verdict

    def copywriter_response(call):
        r = copy_round["n"]
        copy_round["n"] += 1
        _, keys, outcome, _ = expected["rounds"][r]
        events.append(("copywriter", r + 1))
        # D20 — exactly the checker keys or the filtered subset, never their union.
        sent = _slots_from_message(call.message)
        assert [s["variant_key"] for s in sent] == keys
        # Variant_Slots keep their original angle / template_id across rounds (Req 13.4).
        assert [s.get("angle") for s in sent] == [angles_before[k] for k in keys]
        assert [s["template_id"] for s in sent] == [slot_by_key[k]["template_id"] for k in keys]
        if outcome == "copy_error":
            return []  # invalid shape → AgentValidationError (Req 7.10)
        return [_copy(slot_by_key[k], f"R{r + 1}-{k}") for k in keys]

    def prompter_response(call):
        r = prompt_round["n"]
        prompt_round["n"] += 1
        number, keys, outcome = prompter_rounds[r]
        events.append(("image_prompter", number))
        if outcome == "prompt_error":
            return []  # invalid shape → AgentValidationError (Req 7.10)
        return [_prompt(slot_by_key[k], f"PR{number}-{k}") for k in keys]

    run_agent = FakeRunAgent(defaults={
        VALIDADOR_ADSET: validador_response,
        COPYWRITER: copywriter_response,
        IMAGE_PROMPTER: prompter_response,
    })
    h = _make_harness(n_variants, run_agent)
    redis_holder["redis"] = h.redis

    async def run():
        return await jrs._diversity_validation_loop(
            h.deps, h.ad, h.job, plan, list(copies0), list(prompts0),
            project_templates=TEMPLATES,
        )

    import agents.validador_agent as validador_agent_module

    with _patched(
        (jrs, "_run_agent", run_agent),
        (jrs, "_redis", lambda: h.redis),
        (diversity_checker, "check_variants", fake_check_variants),
        # Req 13.2 — any use of the legacy Validador factory is recorded (and must not happen).
        (validador_agent_module, "make_validador_agent", h.factories[VALIDADOR]),
    ):
        result = failure = raised = None
        try:
            result = asyncio.run(run())
        except jrs._AdDiversityFailure as exc:
            failure = exc
        except AgentValidationError as exc:
            raised = exc

    n_checker = sum(1 for e in events if e[0] == "checker")
    n_validador = sum(1 for e in events if e[0] == "validador")
    n_copy_rounds = sum(1 for e in events if e[0] == "copywriter")

    # Bounded loop (Req 7.5); checker every iteration, first (Req 7.1); Validador_Adset
    # only in the iterations without checker errors (Req 7.2, D20).
    assert n_checker == expected["iterations"] <= MAX_ITERATIONS
    assert [e[1] for e in events if e[0] == "validador"] == expected["validador_iterations"]
    assert n_validador == len(expected["validador_iterations"])
    assert expected["validador_iterations"] == [
        it for it in range(1, expected["iterations"] + 1) if not det[it - 1]
    ]
    assert n_copy_rounds == len(expected["rounds"]) <= MAX_ITERATIONS - 1
    # Req 13.2 — only the Validador_Adset, created lazily once per Ad, never custom_prompt.
    assert run_agent.count(VALIDADOR_ADSET) == n_validador
    assert run_agent.count(VALIDADOR) == 0
    # Req 8.6, 13.2 — make_validador_adset_agent at most once per Ad (0 if no iteration
    # reached the Validador_Adset); make_validador_agent never.
    assert h.factories.count(VALIDADOR_ADSET) == (1 if n_validador else 0) <= 1
    assert h.factories.count(VALIDADOR) == 0
    assert h.factories.custom_prompts(VALIDADOR_ADSET) == ([None] if n_validador else [])
    expected_sequence = []
    for it in range(1, expected["iterations"] + 1):
        expected_sequence.append("checker")
        if it in expected["validador_iterations"]:
            expected_sequence.append("validador")
    assert [e[0] for e in events if e[0] in ("checker", "validador")] == expected_sequence
    # Each round regenerates exactly the checker keys (with errors) or the filtered
    # subset (without), never their union; CTAs validated on the new copies.
    for round_it, keys, _, source in expected["rounds"]:
        det_keys = [k for k in slot_keys if k in det[round_it - 1]]
        if source == "checker":
            assert keys == det_keys
        else:
            step = validador[round_it - 1]
            assert not det_keys and keys == [k for k in slot_keys if k in step[2]]
    assert h.ctas.calls == [keys for _, keys, _ in prompter_rounds]
    assert sum(1 for e in events if e[0] == "image_prompter") == len(prompter_rounds)
    # Regenerations only on non-final iterations, never after a Validador_Adset error.
    for round_it, _, _, source in expected["rounds"]:
        assert round_it < MAX_ITERATIONS
        assert source == "checker" or validador[round_it - 1][0] != "error"
    # Creative_Plan and Variant_Slots (template_id, angle) untouched after regenerations,
    # whatever extra keys the verdicts carried (Req 13.4).
    assert plan == plan_before
    assert {s["variant_key"]: s["angle"] for s in plan["variants"]} == angles_before

    final_copies = [exp_copies[k] for k in slot_keys]
    final_prompts = [exp_prompts[k] for k in slot_keys]
    assert _load_cp(h.redis, "copy") == (checkpoint[0] if checkpoint else None)
    assert _load_cp(h.redis, "image_prompts") == (checkpoint[1] if checkpoint else None)

    outcome = expected["outcome"]
    if outcome == "raise":  # Req 7.9
        assert raised is not None and result is None and failure is None
    elif outcome == "det_fail":  # Req 7.6 — fails even if the Validador_Adset never ran
        assert failure is not None and result is None and raised is None
        assert failure.iterations == expected["iterations"] == MAX_ITERATIONS
        assert failure.subset_to_regenerate == expected["subset"]
        assert failure.deterministic_errors == [
            f"scripted error {k}" for k in slot_keys if k in det[-1]
        ]
    else:  # Req 7.7 / approved
        assert result is not None and failure is None and raised is None
        copies, prompts, report, verdict = result
        assert copies == final_copies and prompts == final_prompts
        assert verdict == last_verdict["value"]  # last valid verdict, returned as-is
        assert [c["template_id"] for c in copies] == [s["template_id"] for s in slots]
        assert report["iterations"] == expected["iterations"]
        assert report["deterministic_pass"] is True and report["ad_failed"] is False
        assert report["overall_pass"] is (outcome == "approved")
        assert report["subset_to_regenerate"] == expected["subset"]


# ---------------------------------------------------------------------------
# Property 16 — CTA filtering against the get_ctas catalog
# ---------------------------------------------------------------------------

CTA_POOL = ("LEARN_MORE", "SHOP_NOW", "SIGN_UP", "BOOK_NOW", "CALL", "learn_more",
            "NOT_A_CTA", "", " SHOP_NOW")
CTA_WARNING = "no está en el catálogo de get_ctas"
cta_values = st.one_of(
    st.sampled_from(CTA_POOL),
    st.text(alphabet="ABCDEFGH_ ", max_size=8),
    st.integers(-3, 3),
    st.none(),
)


async def _capture_real_validate_ctas(captured):
    """Run the real `_run_phase1` (flag on, all collaborators faked) up to the
    Diversity_Path hand-off and return the `_validate_ctas` closure it built."""

    async def fake_diversity_path(deps, **kwargs):
        captured["validate_ctas"] = deps.validate_ctas
        return {}

    with _patched((jrs, "_run_adset_diversity_path", fake_diversity_path)):
        await jrs._run_phase1(None, TASK_ID, ID_ADSET, 1, "test-project-id")
    return captured["validate_ctas"]


def _run_copy_step(source, catalog, n_variants, ctas_per_copy):
    """`_load_or_generate_copies_and_prompts` with the real `_validate_ctas`; the copies
    come from the Copywriter (`generated`) or from Checkpoint `copy` (`checkpoint`).
    Returns (copies, CTA warning lines, Copywriter calls)."""
    from tests._diversity_pipeline_fakes import FakeGetCtas, patched_diversity_pipeline

    slots = _slots(n_variants)
    plan = _plan(n_variants)
    raw_copies = []
    for slot, ctas in zip(slots, ctas_per_copy):
        c = _copy(slot, f"H-{slot['variant_key']}")
        c["cta"] = list(ctas)
        raw_copies.append(c)
    prompts = [_prompt(s, f"P-{s['variant_key']}") for s in slots]

    run_agent = FakeRunAgent(defaults={
        COPYWRITER: lambda call: copy.deepcopy(raw_copies),
        IMAGE_PROMPTER: lambda call: copy.deepcopy(prompts),
    })
    redis = FakeRedis()
    if source == "checkpoint":
        redis.set(_cp_key("copy"), json.dumps(raw_copies))
        redis.set(_cp_key("image_prompts"), json.dumps(prompts))

    with patched_diversity_pipeline(
        ad_ids=[AD_ID], redis=redis, run_agent=run_agent,
        get_ctas=FakeGetCtas(ctas=catalog),
    ) as env:
        real_validate_ctas = asyncio.run(_capture_real_validate_ctas({}))
        h = _make_harness(n_variants, run_agent, validate_ctas=real_validate_ctas)
        n_logs_before = len(env.logs.records)
        copies, _ = asyncio.run(
            jrs._load_or_generate_copies_and_prompts(h.deps, h.ad, h.job, plan)
        )
        warnings = [r.message for r in env.logs.records[n_logs_before:]
                    if r.level == "WARNING" and CTA_WARNING in r.message]
    return copies, warnings, run_agent.count(COPYWRITER)


# Feature: adset-creative-diversity, Property 16: Filtrado de CTAs contra el catálogo
@settings(max_examples=100, deadline=None)
@given(
    catalog=st.lists(st.sampled_from(CTA_POOL), max_size=6),
    data=st.data(),
)
def test_property_16_ctas_filtered_against_catalog(catalog, data):
    """**Validates: Requirements 5.4**"""
    n_variants = data.draw(st.integers(1, 3), label="n_variants")
    ctas_per_copy = data.draw(
        # min_size=1: validate_copywriter_response rejects an empty `cta`
        # (ERR_COPY_MISSING_CTA), so neither a valid generation nor a Checkpoint has one.
        st.lists(st.lists(cta_values, min_size=1, max_size=5),
                 min_size=n_variants, max_size=n_variants),
        label="ctas_per_copy",
    )
    expected = [[v for v in ctas if v in catalog] for ctas in ctas_per_copy]
    expected_warnings = [
        f"[{TASK_ID}] copywriter CTA '{v}' no está en el catálogo de get_ctas. Se ajusta a ''."
        for ctas in ctas_per_copy for v in ctas if v not in catalog
    ]

    results = {}
    for source in ("generated", "checkpoint"):
        copies, warnings, copywriter_calls = _run_copy_step(
            source, catalog, n_variants, ctas_per_copy)
        assert copywriter_calls == (1 if source == "generated" else 0)
        # Ordered subsequence of the original values that are in the catalog.
        assert [c["cta"] for c in copies] == expected
        # One warning per removed value.
        assert warnings == expected_warnings
        results[source] = copies

    # Same result whether the copy comes from a Checkpoint or a fresh generation.
    assert results["generated"] == results["checkpoint"]


# ---------------------------------------------------------------------------
# Property 17 — cardinalities of the Diversity_Path (full `_run_phase1`)
# ---------------------------------------------------------------------------

SCENARIOS = ("scenario_1", "scenario_2_present", "scenario_2_absent")


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


@st.composite
def phase1_jobs(draw):
    """`(adset_ad_ids, id_ad, scenario, n_variants, template_ids)`."""
    n_ads = draw(st.integers(1, 4), label="N")
    ad_ids = draw(st.lists(st.integers(1, 10_000), min_size=n_ads, max_size=n_ads,
                           unique=True), label="adset_ad_ids")
    scenario = draw(st.sampled_from(SCENARIOS), label="scenario")
    if scenario == "scenario_1":
        id_ad = None
    elif scenario == "scenario_2_present":
        id_ad = draw(st.sampled_from(ad_ids), label="id_ad")
    else:
        id_ad = draw(st.integers(1, 20_000).filter(lambda x: x not in ad_ids), label="id_ad")
    n_variants = draw(st.integers(1, 8), label="n_variants")
    n_templates = draw(st.integers(1, 4), label="n_templates")
    template_ids = [f"tpl-{i}" for i in range(1, n_templates + 1)]
    return ad_ids, id_ad, scenario, n_variants, template_ids


# Feature: adset-creative-diversity, Property 17: Cardinalidades del Diversity_Path
@settings(max_examples=100, deadline=None)
@given(
    job=phase1_jobs(),
    task_suffix=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1,
                        max_size=16),
)
def test_property_17_diversity_path_cardinalities(job, task_suffix):
    """**Validates: Requirements 2.5, 3.3, 3.7, 4.5, 4.6, 4.9, 4.10, 4.12, 7.2, 7.12, 8.1, 8.6, 12.3, 12.19, 12.20, 14.1**

    P11/P12: every template_id / media_template_id of a processed Ad equals
    `order[ad_slot % len(order)]` with `order = template_order(template_ids, task_id)`;
    Checkpoint `adset_templates` = `{project_templates, template_order: order}`, written
    before any `strategy` Checkpoint (D18). Each Creative_Plan carries the angles
    `assign_variant_angles(plan_ad_{ad_id}, n_variants)`; the Validador_Adset runs exactly
    once per Ad and `make_validador_agent` is never called."""
    from services.adset_diversity import (
        FULL_ADSET_CONTEXT_HEADER,
        assign_variant_angles,
        template_order,
    )
    from tests._diversity_pipeline_fakes import (
        ESTRATEGA_ADSET,
        FakeGetATemplateDefinition,
        FakeGetTemplateContext,
        expected_slots,
        patched_diversity_pipeline,
    )

    ad_ids, id_ad, scenario, n_variants, template_ids = job
    templates = [{"id": t, "name": f"Template {t}", "elements": [], "formats": []}
                 for t in template_ids]
    slot_ad_ids = sorted(ad_ids) + ([id_ad] if scenario == "scenario_2_absent" else [])
    targets = sorted(ad_ids) if scenario == "scenario_1" else [id_ad]
    task_id = f"{TASK_ID}-p17-{task_suffix}"  # generated: Template_Order depends on it

    run_agent = FakeRunAgent(defaults={
        ESTRATEGA_ADSET: [{"index": 0, "concept": "A conforming concept"}],
        COPYWRITER: _conforming_copies,
        IMAGE_PROMPTER: _conforming_prompts,
        VALIDADOR_ADSET: {"overall_pass": True, "subset_to_regenerate": []},
    })
    ctx = make_adset_context(ad_ids)
    # The block every agent message must carry: the sanitised Adset_Context (Req 2.5).
    sanitised_json = json.dumps(jrs._strip_signed_urls(copy.deepcopy(ctx)), ensure_ascii=False)
    context_block = f"{FULL_ADSET_CONTEXT_HEADER}\n{sanitised_json}\n"

    with patched_diversity_pipeline(
        adset_context=ctx, run_agent=run_agent,
        get_template_context=FakeGetTemplateContext(templates=templates),
        get_a_template_definition=FakeGetATemplateDefinition(templates=templates),
    ) as env:
        import agents.validador_agent as validador_agent_module

        # Req 8.6 — the real `agents.validador_agent.make_validador_agent` (the symbol
        # `_run_phase1` imports) is replaced by the recording fake, so any call is counted.
        assert validador_agent_module.make_validador_agent is env.factories[VALIDADOR]
        result = asyncio.run(jrs._run_phase1(
            None, task_id, ID_ADSET, n_variants, "test-project-id", id_ad=id_ad,
        ))  # no ValidationError / AgentValidationError raised

    # get_adset_context and assign_territories once per job (Req 3.3, 3.7).
    assert env.get_adset_context.call_count == 1
    assert env.assign_territories.call_count == 1
    terr_call = env.assign_territories.calls[0]["kwargs"]
    assert terr_call["n_variantes"] == 1 and terr_call["n_ads"] == len(slot_ad_ids)
    # Templates read once per job (Req 4.5, 12.19), shuffled by the job's Template_Order.
    assert env.get_template_context.call_count == 1
    order = template_order(template_ids, task_id)

    # Checkpoint adset_templates (Req 4.10, 4.12, 12.20; D18): one write with the job's
    # Project_Templates and Template_Order, before any `strategy` Checkpoint.
    templates_key = jrs._cp_key(task_id, ID_ADSET, "adset_templates")
    templates_writes = [i for i, s in enumerate(env.redis.sets) if s.key == templates_key]
    assert len(templates_writes) == 1
    assert json.loads(env.redis.sets[templates_writes[0]].value) == {
        "project_templates": template_ids, "template_order": order,
    }
    strategy_keys = {jrs._cp_key(task_id, ad_id, "strategy") for ad_id in targets}
    strategy_writes = [i for i, s in enumerate(env.redis.sets) if s.key in strategy_keys]
    assert len(strategy_writes) >= len(targets)
    assert templates_writes[0] < min(strategy_writes)

    # One agent call per processed Ad (all approved at the first iteration).
    # Req 13.2 — the Diversity_Path uses the Validador_Adset, never the legacy Validador.
    # Req 8.6 — make_validador_agent called 0 times and the legacy Validador never run.
    assert env.factories.count(VALIDADOR) == 0
    assert run_agent.count(VALIDADOR) == 0
    assert env.factories.count(VALIDADOR_ADSET) == len(targets)
    # Req 7.2 — exactly one Validador_Adset invocation per processed Ad (conforming fakes,
    # approval at the first iteration): each Ad's Variant_Slots appear in a single message.
    validador_messages = run_agent.messages_for(VALIDADOR_ADSET)
    for ad_id in targets:
        assert sum(f'"plan_ad_{ad_id}_v1"' in m for m in validador_messages) == 1
    for agent_name in (ESTRATEGA_ADSET, COPYWRITER, IMAGE_PROMPTER, VALIDADOR_ADSET):
        messages = run_agent.messages_for(agent_name)
        assert len(messages) == len(targets)
        for message in messages:  # Req 2.5 — sanitised Adset_Context in every message
            assert context_block in message

    # save_ads once per processed Ad, payloads in slot order (Req 8.1).
    assert sorted(env.save_ads.ad_ids) == targets
    ad_templates = {}
    for ad_id in targets:
        # P11/P12 (D15/D16/D18): one Ad_Template per Ad = order[ad_slot % len(order)],
        # where ad_slot is the Ad's index in slot_ad_ids (the extra slot included).
        ad_slot = slot_ad_ids.index(ad_id)
        ad_template = order[ad_slot % len(order)]
        ad_templates[ad_id] = ad_template
        expected_templates = [ad_template] * n_variants
        plan = env.checkpoint(task_id, ad_id, "strategy")
        slots = plan["variants"]
        assert plan["id"] == f"plan_ad_{ad_id}"
        assert len(slots) == n_variants  # Req 4.9
        # Variant_Slots with their Variant_Angle (P14, D22; Req 14.1).
        assert slots == expected_slots(plan["id"], n_variants, ad_template)
        # Req 14.1 — the Creative_Plan's angles are exactly
        # assign_variant_angles(plan_ad_{ad_id}, n_variants), in slot order.
        assert [s["angle"] for s in slots] == assign_variant_angles(f"plan_ad_{ad_id}",
                                                                    n_variants)
        copies = env.checkpoint(task_id, ad_id, "copy")
        prompts = env.checkpoint(task_id, ad_id, "image_prompts")
        assert [c["variant_key"] for c in copies] == [s["variant_key"] for s in slots]
        assert [p["variant_key"] for p in prompts] == [s["variant_key"] for s in slots]
        assert [c["template_id"] for c in copies] == expected_templates
        (payloads,) = [c.arguments["payloads"] for c in env.save_ads.calls
                       if c.arguments["id_ad"] == ad_id]
        assert [p["media_template_id"] for p in payloads] == expected_templates
        (abyssale_payload,) = [c.arguments["abyssale_payload"]
                               for c in env.post_to_abyssale.calls
                               if c.arguments["ad_id"] == ad_id]
        assert [e["template_id"] for e in abyssale_payload["elements"]] == expected_templates
    # Req 12.20 (a): enough templates → distinct Ad_Templates and no 6.12 issue.
    if len(slot_ad_ids) <= len(template_ids):
        assert len(set(ad_templates.values())) == len(targets)
        assert not any("share Ad_Template" in e for r in result["diversity_reports"]
                       for e in r["deterministic_errors"])

    # One Diversity_Report per processed Ad (Req 7.12).
    reports = result["diversity_reports"]
    assert sorted(r["ad_id"] for r in reports) == targets
    for r in reports:
        assert r["ad_failed"] is False and r["deterministic_pass"] is True
        assert r["overall_pass"] is True and r["iterations"] == 1
    assert len(result["saved_ads"]) == len(targets) * n_variants
    assert all(s["saved"] for s in result["saved_ads"])
    assert len(result["proposals"]) == len(targets) * n_variants
    assert len(result["abyssale_batch_ids"]) == len(targets)
    # No real waits: the final webhook wait went through the fake sleep.
    assert jrs._ABYSSALE_WEBHOOK_WAIT_S in env.sleep.calls


# ---------------------------------------------------------------------------
# Property 18 — delete_variants conditions and ordering (full `_run_phase1`)
# ---------------------------------------------------------------------------
SAVE_OUTCOMES = ("ok", "exception", "ok_false", "empty_list")
ABYSSALE_OUTCOMES = ("str", "list", "list_with_blank", "empty_str", "none", "empty_list",
                     "exception")
ABYSSALE_OK = {"str", "list", "list_with_blank"}
def _save_ads_outcome(kind):
    if kind == "exception":
        return RuntimeError("scripted save_ads failure")
    if kind == "ok_false":
        return {"ok": False, "error": "scripted"}
    if kind == "empty_list":
        return []
    return None  # DEFAULT (Sinergia-shaped success)
def _abyssale_outcome(kind, ad_id):
    if kind == "exception":
        return RuntimeError("scripted Abyssale failure")
    batch_id = {
        "str": f"batch-{ad_id}",
        "list": [f"batch-{ad_id}-a", f"batch-{ad_id}-b"],
        "list_with_blank": ["", f"batch-{ad_id}"],
        "empty_str": "",
        "none": None,
        "empty_list": [],
    }[kind]
    return {"ok": True, "status": "WAITING_ABYSSALE", "batch_id": batch_id,
            "abyssale_response": []}
# Feature: adset-creative-diversity, Property 18: Condiciones de delete_variants
@settings(max_examples=100, deadline=None)
@given(
    ad_ids=st.lists(st.integers(1, 10_000), min_size=1, max_size=3, unique=True),
    data=st.data(),
    n_variants=st.integers(1, 3),
    add_variant=st.sampled_from([True, False, None]),
    id_variant=st.one_of(st.none(), st.just([]),
                         st.lists(st.integers(1, 99_999), min_size=1, max_size=4)),
    save_kind=st.sampled_from(SAVE_OUTCOMES),
    abyssale_kind=st.sampled_from(ABYSSALE_OUTCOMES),
)
def test_property_18_delete_variants_conditions(
    ad_ids, data, n_variants, add_variant, id_variant, save_kind, abyssale_kind,
):
    """**Validates: Requirements 8.3, 8.4, 8.5, 8.7**"""
    from tests._diversity_pipeline_fakes import (
        DEFAULT,
        ESTRATEGA_ADSET,
        FakePostToAbyssaleAndWait,
        FakeSaveAds,
        patched_diversity_pipeline,
    )
    id_ad = data.draw(st.sampled_from(ad_ids), label="id_ad")
    task_id = f"{TASK_ID}-p18"
    save_outcome = _save_ads_outcome(save_kind)
    save_ads = FakeSaveAds([DEFAULT if save_outcome is None else save_outcome])
    abyssale = FakePostToAbyssaleAndWait([_abyssale_outcome(abyssale_kind, id_ad)])
    run_agent = FakeRunAgent(defaults={
        ESTRATEGA_ADSET: [{"index": 0, "concept": "A conforming concept"}],
        COPYWRITER: _conforming_copies,
        IMAGE_PROMPTER: _conforming_prompts,
        VALIDADOR_ADSET: {"overall_pass": True, "subset_to_regenerate": []},
    })
    with patched_diversity_pipeline(
        ad_ids=ad_ids, run_agent=run_agent, save_ads=save_ads, post_to_abyssale=abyssale,
    ) as env:
        result = asyncio.run(jrs._run_phase1(
            None, task_id, ID_ADSET, n_variants, "test-project-id", id_ad=id_ad,
            add_variant=add_variant, id_variant=id_variant,
        ))
    save_ok = save_kind == "ok"
    abyssale_ok = abyssale_kind in ABYSSALE_OK
    variant_ok = add_variant is not True and bool(id_variant)
    expected_delete = variant_ok and save_ok and abyssale_ok
    # Exactly one Ad processed (scenario 2), one save_ads and one Abyssale submission.
    assert env.save_ads.ad_ids == [id_ad]
    assert [c.arguments["ad_id"] for c in env.post_to_abyssale.calls] == [id_ad]
    assert any(s.get("saved") for s in result["saved_ads"]) is save_ok
    deletes = env.events.of("delete_variants")
    if expected_delete:
        # Req 8.3 — exactly once in the job, with id_variant, after Abyssale for id_ad.
        assert len(deletes) == 1
        assert deletes[0].arguments["variant_ids"] == id_variant
        abyssale_pos = [i for i, e in enumerate(env.events)
                        if e.name == "post_to_abyssale_and_wait"
                        and e.arguments.get("ad_id") == id_ad]
        assert abyssale_pos and env.events.index_of("delete_variants") > abyssale_pos[-1]
    else:
        # Req 8.4, 8.5, 8.7 — no deletion.
        assert deletes == []
        assert env.delete_variants.call_count == 0
    # Req 8.5, 8.7 — a skip caused by save_ads or Abyssale logs a warning with task/ad ids.
    if variant_ok and not (save_ok and abyssale_ok):
        skip_warnings = [
            r.message for r in env.logs.records
            if r.level == "WARNING" and "delete_variants skipped" in r.message
        ]
        assert any(f"[{task_id}]" in m and f"ad={id_ad}" in m for m in skip_warnings)
    # Req 8.4 — add_variant=True never logs a deletion warning.
    if add_variant is True:
        assert not any(r.level == "WARNING" and "delete_variants skipped" in r.message
                       for r in env.logs.records)


# ---------------------------------------------------------------------------
# Property 23 — resumption from Checkpoints (full `_run_phase1`, same task_id)
# ---------------------------------------------------------------------------
AD_CHECKPOINT_STEPS = ("strategy", "copy", "image_prompts")


def _p23_run_agent():
    from tests._diversity_pipeline_fakes import ESTRATEGA_ADSET

    return FakeRunAgent(defaults={
        ESTRATEGA_ADSET: [{"index": 0, "concept": "A conforming concept"}],
        COPYWRITER: _conforming_copies,
        IMAGE_PROMPTER: _conforming_prompts,
        VALIDADOR_ADSET: {"overall_pass": True, "subset_to_regenerate": []},
    })


def _p23_run(task_id, ad_ids, id_ad, n_variants, redis):
    """One `_run_phase1` on `redis`; returns (env, run_agent, result)."""
    from tests._diversity_pipeline_fakes import patched_diversity_pipeline

    run_agent = _p23_run_agent()
    with patched_diversity_pipeline(ad_ids=ad_ids, redis=redis, run_agent=run_agent) as env:
        result = asyncio.run(jrs._run_phase1(
            None, task_id, ID_ADSET, n_variants, "test-project-id", id_ad=id_ad,
        ))
    return env, run_agent, result


def _p23_agent_ads(run_agent, agent_name, suffix):
    """Ad ids for which `agent_name` was invoked (from `adset_{id}_ad_{ad}_div_{suffix}`)."""
    marker = f"_div_{suffix}"
    return sorted(int(c.user_id.split("_ad_", 1)[1].split(marker, 1)[0])
                  for c in run_agent.calls_for(agent_name) if c.user_id.endswith(marker))


def _p23_sent_angles(run_agent, agent_name, suffix, ad_id):
    """Variant_Angles (slot order) sent to `agent_name` for `ad_id`, one list per call."""
    user_id = f"_ad_{ad_id}_div_{suffix}"
    return [[s.get("angle") for s in _slots_from_message(c.message)]
            for c in run_agent.calls_for(agent_name) if c.user_id.endswith(user_id)]


# Req 4.8, 14.5, 12.28 (P14, D22) — how the `angle`s of a seeded `strategy` Checkpoint
# are edited before the retry: kept as stored (`saved`), replaced by other valid and
# mutually distinct vocabulary entries (`valid_other`), or broken in a non-empty subset
# of slots by dropping the key or storing an angle outside Angle_Vocabulary (`broken`).
P23_ANGLE_MODES = ("saved", "valid_other", "broken")


def _p23_foreign_angles():
    from services.adset_diversity import ANGLE_KEYS, ANGLE_VOCABULARY, is_valid_variant_angle

    vocab = st.sampled_from(ANGLE_VOCABULARY)
    return st.one_of(
        st.none(),
        st.text(max_size=8),
        st.integers(),
        st.lists(st.text(max_size=3), max_size=3),
        st.fixed_dictionaries({k: st.text(max_size=8) for k in ANGLE_KEYS}),
        vocab.map(lambda a: {**a, "extra": "x"}),
        st.tuples(vocab, st.sampled_from(ANGLE_KEYS)).map(
            lambda t: {k: v for k, v in t[0].items() if k != t[1]}),
        st.tuples(vocab, st.sampled_from(ANGLE_KEYS), st.text(max_size=8)).map(
            lambda t: {**t[0], t[1]: f"zz_{t[2]}"}),
    ).filter(lambda a: not is_valid_variant_angle(a))


@st.composite
def p23_angle_edits(draw, plan_id, n_variants):
    """`(mode, edit)` with `edit(slots) -> slots` applied to a `strategy` Checkpoint."""
    from services.adset_diversity import ANGLE_VOCABULARY, assign_variant_angles

    mode = draw(st.sampled_from(P23_ANGLE_MODES), label=f"angle_mode_{plan_id}")
    fresh = assign_variant_angles(plan_id, n_variants)
    if mode == "saved":
        return mode, lambda slots: slots
    if mode == "valid_other":
        others = draw(
            st.permutations(range(len(ANGLE_VOCABULARY)))
            .map(lambda p: [dict(ANGLE_VOCABULARY[i]) for i in p[:n_variants]])
            .filter(lambda angles: angles != fresh),
            label=f"valid_angles_{plan_id}",
        )
        return mode, lambda slots: [{**s, "angle": a} for s, a in zip(slots, others)]
    broken = draw(st.dictionaries(
        st.integers(0, n_variants - 1),
        st.one_of(st.just("missing"), _p23_foreign_angles().map(lambda a: ("foreign", a))),
        min_size=1,
    ), label=f"broken_angles_{plan_id}")

    def edit(slots):
        out = []
        for k, slot in enumerate(slots):
            slot = dict(slot)
            if broken.get(k) == "missing":
                slot.pop("angle", None)
            elif k in broken:
                slot["angle"] = broken[k][1]
            out.append(slot)
        return out

    return mode, edit


# Feature: adset-creative-diversity, Property 23: Reanudación por Checkpoints
@settings(max_examples=100, deadline=None)
@given(
    ad_ids=st.lists(st.integers(1, 10_000), min_size=1, max_size=3, unique=True),
    data=st.data(),
    n_variants=st.integers(1, 3),
    keep_territories=st.booleans(),
)
def test_property_23_resumption_from_checkpoints(ad_ids, data, n_variants, keep_territories):
    """**Validates: Requirements 3.13, 4.8, 4.12, 5.6, 12.15, 12.20, 12.28, 14.5**"""
    from unittest import mock

    from services.adset_diversity import (
        assign_variant_angles,
        is_valid_variant_angle,
        template_order,
    )
    from tests._diversity_pipeline_fakes import ESTRATEGA_ADSET, expected_slots, mock_template_ids

    scenario_2 = data.draw(st.booleans(), label="scenario_2")
    id_ad = data.draw(st.sampled_from(ad_ids), label="id_ad") if scenario_2 else None
    targets = [id_ad] if scenario_2 else sorted(ad_ids)
    kept = {
        ad_id: data.draw(st.frozensets(st.sampled_from(AD_CHECKPOINT_STEPS)),
                         label=f"checkpoints_ad_{ad_id}")
        for ad_id in targets
    }
    task_id = f"{TASK_ID}-p23"
    territories_key = jrs._cp_key(task_id, ID_ADSET, "adset_territories")
    # D18: `adset_templates` is keyed by id_adset (job-level Checkpoint).
    templates_key = jrs._cp_key(task_id, ID_ADSET, "adset_templates")
    # D18: a `strategy` Checkpoint only exists if `adset_templates` exists, so it is
    # kept whenever any `strategy` is kept; otherwise it is kept optionally.
    any_strategy = any("strategy" in steps for steps in kept.values())
    keep_templates = True if any_strategy else data.draw(st.booleans(), label="keep_templates")

    # Req 4.12, 12.20; P12, D18 — when `adset_templates` is kept and there are ≥ 2
    # templates, the job's Template_Order is a permutation different from the one the
    # task_id seed produces. It is preloaded in the *original* execution, so every
    # Checkpoint derives from it (strategy coherent with it, task 19.3); the retry
    # must reuse it verbatim instead of recomputing.
    project_templates = mock_template_ids()
    seed_order = template_order(project_templates, task_id)
    order = seed_order
    original_redis = FakeRedis()
    if keep_templates and len(project_templates) >= 2:
        order = data.draw(
            st.permutations(project_templates).filter(lambda p: list(p) != seed_order),
            label="non_seed_template_order",
        )
        order = list(order)
        original_redis.data[templates_key] = json.dumps(
            {"project_templates": project_templates, "template_order": order}
        )

    # Original execution: produces every Checkpoint with valid content.
    _p23_run(task_id, ad_ids, id_ad, n_variants, original_redis)
    original = dict(original_redis.data)
    assert json.loads(original[templates_key]) == {
        "project_templates": project_templates, "template_order": order,
    }
    assert territories_key in original
    assert templates_key in original
    for ad_id in targets:
        for step in AD_CHECKPOINT_STEPS:
            assert jrs._cp_key(task_id, ad_id, step) in original

    # Retry with the same task_id and only the chosen subset of Checkpoints.
    seeded = {}
    if keep_territories:
        seeded[territories_key] = original[territories_key]
    if keep_templates:
        seeded[templates_key] = original[templates_key]
    # Req 4.8, 14.5, 12.28 (P14, D22) — each kept `strategy` Checkpoint keeps its valid
    # angles, gets other valid ones, or has some slots without `angle` / with a foreign one.
    angle_modes, expected_angles = {}, {}
    for ad_id, steps in kept.items():
        for step in steps:
            key = jrs._cp_key(task_id, ad_id, step)
            seeded[key] = original[key]
        plan_id = f"plan_ad_{ad_id}"
        expected_angles[ad_id] = assign_variant_angles(plan_id, n_variants)
        if "strategy" in steps:
            mode, edit = data.draw(p23_angle_edits(plan_id, n_variants),
                                   label=f"angle_edit_ad_{ad_id}")
            angle_modes[ad_id] = mode
            key = jrs._cp_key(task_id, ad_id, "strategy")
            stored = json.loads(original[key])
            stored["variants"] = edit(stored["variants"])
            seeded[key] = json.dumps(stored)
            if mode == "valid_other":
                # Valid angles are reused as stored, never recomputed.
                expected_angles[ad_id] = [s["angle"] for s in stored["variants"]]
            elif mode == "broken":
                assert not all(is_valid_variant_angle(s.get("angle"))
                               for s in stored["variants"])
    retry_redis = FakeRedis()
    retry_redis.data.update(seeded)
    # Req 4.12, 12.20 — with `adset_templates` seeded, template_order must not be invoked.
    order_guard = (
        mock.patch("services.adset_diversity.template_order",
                   side_effect=AssertionError("template_order must not be invoked"))
        if keep_templates else contextlib.nullcontext()
    )
    with order_guard as guarded_template_order:
        env, run_agent, result = _p23_run(task_id, ad_ids, id_ad, n_variants, retry_redis)
    if keep_templates:
        assert guarded_template_order.call_count == 0

    # Req 3.13 — assign_territories skipped iff the adset_territories Checkpoint exists.
    assert env.assign_territories.call_count == (0 if keep_territories else 1)
    # Req 4.8 — no Estratega_Adset for Ads with `strategy`.
    no_strategy = sorted(a for a in targets if "strategy" not in kept[a])
    assert _p23_agent_ads(run_agent, ESTRATEGA_ADSET, "strat") == no_strategy
    assert run_agent.count(ESTRATEGA_ADSET) == len(no_strategy)
    # Req 4.12, 12.20 — get_template_context skipped iff `adset_templates` is seeded,
    # otherwise read exactly once per job.
    assert env.get_template_context.call_count == (0 if keep_templates else 1)
    assert json.loads(retry_redis.data[templates_key]) == json.loads(original[templates_key])
    # Req 5.6 — no Copywriter / Image_Prompter for Ads with `copy` / `image_prompts`
    # (Validador approves at once: no regenerations of the loop).
    assert _p23_agent_ads(run_agent, COPYWRITER, "copy") == \
        sorted(a for a in targets if "copy" not in kept[a])
    assert _p23_agent_ads(run_agent, IMAGE_PROMPTER, "img") == \
        sorted(a for a in targets if "image_prompts" not in kept[a])
    assert run_agent.count(VALIDADOR_ADSET) == len(targets)
    assert env.factories.count(VALIDADOR) == 0

    # Same Ad_Territories, Creative_Plans and Variant_Slots as the original execution.
    assert json.loads(retry_redis.data[territories_key]) == json.loads(original[territories_key])
    for ad_id in targets:
        for step in ("copy", "image_prompts"):
            key = jrs._cp_key(task_id, ad_id, step)
            assert json.loads(retry_redis.data[key]) == json.loads(original[key])
        strategy_key = jrs._cp_key(task_id, ad_id, "strategy")
        plan = json.loads(retry_redis.data[strategy_key])
        assert plan["id"] == f"plan_ad_{ad_id}" and len(plan["variants"]) == n_variants
        # P11 — the retry keeps the same Variant_Slots and the same Ad_Template
        # (`order[ad_slot % len(order)]`) as the original execution, down to save_ads/Abyssale.
        original_plan = json.loads(original[strategy_key])
        ad_slot = sorted(ad_ids).index(ad_id)
        ad_template = order[ad_slot % len(order)]
        expected_templates = [ad_template] * n_variants
        # Variant_Slots with their Variant_Angle (P14, D22; Req 14.1, 14.5).
        assert original_plan["variants"] == expected_slots(plan["id"], n_variants, ad_template)
        # Req 4.8, 14.5, 12.28 — valid stored angles are kept as stored; a slot without
        # `angle` or with a foreign one makes the code recompute all of them with
        # assign_variant_angles(plan_id, n_variants) (= the original angles). Everything
        # else in the Creative_Plan is unchanged.
        mode = angle_modes.get(ad_id)
        angles = expected_angles[ad_id]
        assert plan == {
            **original_plan,
            "variants": [{**s, "angle": a} for s, a in zip(original_plan["variants"], angles)],
        }
        if mode != "valid_other":
            assert angles == assign_variant_angles(plan["id"], n_variants)
            assert plan == original_plan
            assert plan["variants"] == expected_slots(plan["id"], n_variants, ad_template)
        # The corrected plan is stored again only when its angles were recomputed;
        # a reused valid one is not rewritten; a fresh one is written once.
        strategy_writes = [k for k in retry_redis.written_keys if k == strategy_key]
        assert len(strategy_writes) == (0 if mode in ("saved", "valid_other") else 1)
        # The Copywriter receives exactly these angles, in slot order (only the
        # Copywriter gets them, Req 14.6).
        if "copy" not in kept[ad_id]:
            assert _p23_sent_angles(run_agent, COPYWRITER, "copy", ad_id) == [angles]
        (payloads,) = [c.arguments["payloads"] for c in env.save_ads.calls
                       if c.arguments["id_ad"] == ad_id]
        assert [p["media_template_id"] for p in payloads] == expected_templates
        (abyssale_payload,) = [c.arguments["abyssale_payload"]
                               for c in env.post_to_abyssale.calls
                               if c.arguments["ad_id"] == ad_id]
        assert [e["template_id"] for e in abyssale_payload["elements"]] == expected_templates
    assert sorted(r["ad_id"] for r in result["diversity_reports"]) == targets
    assert all(r["ad_failed"] is False for r in result["diversity_reports"])


# ---------------------------------------------------------------------------
# Property 24 — Ad_Template allocation across Ad_Slots (Scenario_2, full `_run_phase1`)
# ---------------------------------------------------------------------------

# Feature: adset-creative-diversity, Property 24: Reparto de Ad_Templates entre Ad_Slots
@settings(max_examples=100, deadline=None)
@given(
    ad_ids=st.lists(st.integers(1, 10_000), min_size=1, max_size=4, unique=True),
    data=st.data(),
    n_templates=st.integers(1, 4),
    n_variants=st.integers(1, 3),
    task_suffix=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1,
                        max_size=16),
)
def test_property_24_ad_template_allocation_scenario_2(
    ad_ids, data, n_templates, n_variants, task_suffix,
):
    """**Validates: Requirements 4.6, 6.12, 12.20**

    Scenario_2: the Ad `id_ad` in Ad_Slot `s` receives `order[s % len(order)]`
    (`order = template_order(templates, task_id)`), distinct from the Ad_Templates that
    `order` assigns to its sibling Ad_Slots when the number of Ad_Slots is
    ≤ len(templates); when `id_ad` is not in the Adset (Req 3.6), its extra Ad_Slot
    `len(Adset_Ads)` receives `order[len(Adset_Ads) % len(order)]`."""
    from services.adset_diversity import template_order
    from tests._diversity_pipeline_fakes import (
        ESTRATEGA_ADSET,
        FakeGetATemplateDefinition,
        FakeGetTemplateContext,
        patched_diversity_pipeline,
    )

    present = data.draw(st.booleans(), label="id_ad_in_adset")
    if present:
        id_ad = data.draw(st.sampled_from(ad_ids), label="id_ad")
    else:
        id_ad = data.draw(st.integers(1, 20_000).filter(lambda x: x not in ad_ids),
                          label="id_ad")
    template_ids = [f"tpl-{i}" for i in range(1, n_templates + 1)]
    templates = [{"id": t, "name": f"Template {t}", "elements": [], "formats": []}
                 for t in template_ids]
    slot_ad_ids = sorted(ad_ids) + ([] if present else [id_ad])
    n_slots = len(slot_ad_ids)
    task_id = f"{TASK_ID}-p24-{task_suffix}"

    run_agent = FakeRunAgent(defaults={
        ESTRATEGA_ADSET: [{"index": 0, "concept": "A conforming concept"}],
        COPYWRITER: _conforming_copies,
        IMAGE_PROMPTER: _conforming_prompts,
        VALIDADOR_ADSET: {"overall_pass": True, "subset_to_regenerate": []},
    })
    with patched_diversity_pipeline(
        adset_context=make_adset_context(ad_ids), run_agent=run_agent,
        get_template_context=FakeGetTemplateContext(templates=templates),
        get_a_template_definition=FakeGetATemplateDefinition(templates=templates),
    ) as env:
        result = asyncio.run(jrs._run_phase1(
            None, task_id, ID_ADSET, n_variants, "test-project-id", id_ad=id_ad,
        ))

    order = template_order(template_ids, task_id)
    ad_slot = slot_ad_ids.index(id_ad)
    if not present:  # Req 3.6 — extra Ad_Slot right after the Adset_Ads
        assert ad_slot == len(ad_ids)
    expected = order[ad_slot % len(order)]
    if not present:
        assert expected == order[len(ad_ids) % len(order)]

    # Only id_ad is processed; all its variants carry the Ad_Template of its Ad_Slot.
    assert env.save_ads.ad_ids == [id_ad]
    plan = env.checkpoint(task_id, id_ad, "strategy")
    assert [s["template_id"] for s in plan["variants"]] == [expected] * n_variants
    (payloads,) = [c.arguments["payloads"] for c in env.save_ads.calls
                   if c.arguments["id_ad"] == id_ad]
    assert [p["media_template_id"] for p in payloads] == [expected] * n_variants

    # Req 6.12, 12.20 (c) — no collision with the siblings' Ad_Templates in the same order.
    sibling_templates = {order[j % len(order)] for j in range(n_slots) if j != ad_slot}
    (report,) = result["diversity_reports"]
    assert report["ad_id"] == id_ad and report["ad_failed"] is False
    if n_slots <= len(template_ids):
        assert expected not in sibling_templates
        assert not any("share Ad_Template" in m for m in
                       report["deterministic_errors"] + report["deterministic_warnings"])
    else:  # rotation: never an error of 6.12, the job continues
        assert not any("share Ad_Template" in m for m in report["deterministic_errors"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
