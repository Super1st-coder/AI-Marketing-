"""Property tests for the Variant_Angle assignment of services/adset_diversity.py
(adset-creative-diversity, task 24.5, Property 26, Decision P14/D22).
Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_angles.py
"""
import copy
import hashlib
import random

from hypothesis import given, settings
from hypothesis import strategies as st

from services.adset_diversity import (
    ANGLE_VOCABULARY,
    angle_offset,
    assign_variant_angles,
    ensure_variant_angles,
    is_valid_variant_angle,
    template_order,
)

SIZE = len(ANGLE_VOCABULARY)
VOCAB_SNAPSHOT = copy.deepcopy([dict(a) for a in ANGLE_VOCABULARY])

plan_ids = st.one_of(
    st.integers(min_value=0, max_value=10**9).map(lambda n: f"plan_ad_{n}"),
    st.just(""),
    st.text(),  # arbitrary Unicode
)
n_variants_st = st.integers(min_value=1, max_value=2 * SIZE + 5)
valid_angles = st.sampled_from(ANGLE_VOCABULARY).map(dict)


def _oracle(plan_id: str, n: int) -> list[dict]:
    offset = int(hashlib.sha256(plan_id.encode("utf-8")).hexdigest(), 16) % SIZE
    return [dict(ANGLE_VOCABULARY[(offset + k - 1) % SIZE]) for k in range(1, n + 1)]


@st.composite
def foreign_angles(draw):
    """A value that is NOT a valid Variant_Angle (the ``"__missing__"`` marker drops the key)."""
    base = dict(draw(valid_angles))
    kind = draw(st.sampled_from(
        ["missing", "none", "string", "fewer_keys", "extra_keys", "other_value"]))
    if kind == "missing":
        return "__missing__"
    if kind == "none":
        return None
    if kind == "string":
        return draw(st.text())
    if kind == "fewer_keys":
        key = draw(st.sampled_from(sorted(base)))
        del base[key]
        return base
    if kind == "extra_keys":
        base[draw(st.text(min_size=1).filter(lambda k: k not in base))] = draw(st.text())
        return base
    # other_value: one key gets a value no vocabulary entry would produce with the rest
    key = draw(st.sampled_from(sorted(base)))
    base[key] = draw(st.text().filter(lambda v: v != base[key]))
    if is_valid_variant_angle(base):  # cannot happen with the current vocabulary
        base[key] = base[key] + "\u0000foreign"
    return base


def _plan(plan_id: str, angles: list) -> dict:
    variants = []
    for k, angle in enumerate(angles, start=1):
        slot = {"variant_key": f"{plan_id}_v{k}", "template_id": f"tpl_{k % 3}", "extra": k}
        if angle != "__missing__":
            slot["angle"] = angle
        variants.append(slot)
    return {"id": plan_id, "concept": "c", "ad_slot": 0, "variants": variants}


# Feature: adset-creative-diversity, Property 26: Asignación determinista de Variant_Angles
@settings(max_examples=100, deadline=None)
@given(plan_id=plan_ids, n=n_variants_st,
       task_ids=st.lists(st.text(), min_size=1, max_size=3),
       templates=st.lists(st.text(min_size=1), min_size=1, max_size=5, unique=True))
def test_assign_variant_angles_is_deterministic(plan_id, n, task_ids, templates):
    """**Validates: Requirements 14.2, 14.3, 14.9, 12.25, 12.28**"""
    state = random.getstate()
    angles = assign_variant_angles(plan_id, n)
    assert random.getstate() == state

    # Oracle with hashlib.
    assert angle_offset(plan_id) == int(hashlib.sha256(plan_id.encode("utf-8")).hexdigest(), 16) % SIZE
    assert angles == _oracle(plan_id, n)
    assert len(angles) == n
    assert all(is_valid_variant_angle(a) for a in angles)

    # Pairwise distinct while n <= len; period len otherwise.
    if n <= SIZE:
        assert all(angles[i] != angles[j] for i in range(n) for j in range(i + 1, n))
    else:
        assert all(angles[k] == angles[k + SIZE] for k in range(n - SIZE))

    # Independent of any task_id / Template_Order used in the same process.
    for task_id in task_ids:
        template_order(templates, task_id)
        assert assign_variant_angles(plan_id, n) == angles

    # Mutating the result alters neither the constant nor a later call.
    for a in angles:
        a["hook"] = "mutated"
        a.pop("copy_length", None)
    assert [dict(a) for a in ANGLE_VOCABULARY] == VOCAB_SNAPSHOT
    assert assign_variant_angles(plan_id, n) == _oracle(plan_id, n)


# Feature: adset-creative-diversity, Property 26: Asignación determinista de Variant_Angles
@settings(max_examples=100, deadline=None)
@given(data=st.data(), plan_id=plan_ids, n=n_variants_st)
def test_ensure_variant_angles_recomputes_foreign_angles(data, plan_id, n):
    """**Validates: Requirements 14.5, 14.9, 12.25, 12.28**"""
    bad = data.draw(st.sets(st.integers(min_value=0, max_value=n - 1), min_size=1))
    angles = [data.draw(foreign_angles()) if i in bad else data.draw(valid_angles)
              for i in range(n)]
    plan = _plan(plan_id, angles)
    snapshot = copy.deepcopy(plan)

    fixed, recomputed = ensure_variant_angles(plan)

    assert recomputed is True
    assert plan == snapshot  # input not mutated
    assert [s["angle"] for s in fixed["variants"]] == assign_variant_angles(plan_id, n)
    for before, after in zip(snapshot["variants"], fixed["variants"]):
        assert {k: v for k, v in after.items() if k != "angle"} == \
            {k: v for k, v in before.items() if k != "angle"}
    assert {k: v for k, v in fixed.items() if k != "variants"} == \
        {k: v for k, v in snapshot.items() if k != "variants"}


# Feature: adset-creative-diversity, Property 26: Asignación determinista de Variant_Angles
@settings(max_examples=100, deadline=None)
@given(plan_id=plan_ids,
       angles=st.lists(valid_angles, min_size=1, max_size=2 * SIZE + 5))
def test_ensure_variant_angles_keeps_valid_angles(plan_id, angles):
    """Valid angles, even repeated, are reused as is.

    **Validates: Requirements 14.5, 12.25, 12.28**"""
    plan = _plan(plan_id, angles)
    snapshot = copy.deepcopy(plan)

    result, recomputed = ensure_variant_angles(plan)

    assert recomputed is False
    assert result is plan
    assert result == snapshot


# --- Property 27 (task 25.2): oracle of rule 6.13 -----------------------------------

from services.adset_diversity import build_variant_slots  # noqa: E402
from services.diversity_checker import (  # noqa: E402
    ANGLE_MISSING,
    ANGLE_NOT_IN_VOCABULARY,
    ANGLE_REPEATED,
    check_variant_angles,
)


def _angle_oracle(plan: dict, n_variants: int):
    """Expected (errors, warnings) as lists of (code, variant_keys)."""
    errors, valid = [], []
    for slot in plan["variants"]:
        key = slot["variant_key"]
        angle = slot.get("angle")
        if angle is None:
            errors.append((ANGLE_MISSING, (key,)))
        elif not any(angle == dict(a) for a in VOCAB_SNAPSHOT) or not isinstance(angle, dict):
            errors.append((ANGLE_NOT_IN_VOCABULARY, (key,)))
        else:
            valid.append((key, angle))
    repeated = [(ANGLE_REPEATED, (valid[i][0], valid[j][0]))
                for i in range(len(valid)) for j in range(i + 1, len(valid))
                if valid[i][1] == valid[j][1]]
    if n_variants > SIZE:
        return errors, repeated
    return errors + repeated, []


def _codes(issues) -> list:
    return [(issue.code, tuple(issue.variant_keys)) for issue in issues]


# Feature: adset-creative-diversity, Property 27: Oráculo de la regla 6.13 del Diversity_Checker
@settings(max_examples=100, deadline=None)
@given(data=st.data(), plan_id=plan_ids,
       n=st.integers(min_value=1, max_value=2 * SIZE + 1),
       pool_size=st.integers(min_value=1, max_value=SIZE))
def test_check_variant_angles_matches_oracle(data, plan_id, n, pool_size):
    """**Validates: Requirements 6.1, 6.10, 6.13, 12.25**"""
    # A small pool of vocabulary entries forces deliberate repetitions.
    pool = [dict(a) for a in ANGLE_VOCABULARY[:pool_size]]
    bad = data.draw(st.sets(st.integers(min_value=0, max_value=n - 1)))
    angles = [data.draw(foreign_angles()) if i in bad else dict(data.draw(st.sampled_from(pool)))
              for i in range(n)]
    n_variants = data.draw(st.one_of(st.just(n), st.integers(min_value=1, max_value=3 * SIZE)))
    plan = _plan(plan_id, angles)
    snapshot = copy.deepcopy(plan)

    result = check_variant_angles(plan, n_variants)

    expected_errors, expected_warnings = _angle_oracle(snapshot, n_variants)
    assert _codes(result.errors) == expected_errors
    assert _codes(result.warnings) == expected_warnings
    for issue in result.errors + result.warnings:
        assert repr(plan_id) in issue.message
    assert plan == snapshot  # input not mutated
    assert check_variant_angles(plan, n_variants) == result  # deterministic


# Feature: adset-creative-diversity, Property 27: Oráculo de la regla 6.13 del Diversity_Checker
@settings(max_examples=100, deadline=None)
@given(plan_id=plan_ids, ad_slot=st.integers(min_value=0, max_value=20),
       n_variants=st.integers(min_value=1, max_value=2 * SIZE + 1),
       templates=st.lists(st.text(min_size=1), min_size=1, max_size=5, unique=True))
def test_check_variant_angles_on_built_slots(plan_id, ad_slot, n_variants, templates):
    """**Validates: Requirements 6.10, 6.13, 12.25**"""
    slots = [dict(s) for s in build_variant_slots(plan_id, ad_slot, n_variants, templates)]
    plan = {"id": plan_id, "ad_slot": ad_slot, "variants": slots}

    result = check_variant_angles(plan, n_variants)

    assert result.errors == ()
    if n_variants <= SIZE:
        assert result.warnings == ()
    else:
        assert result.warnings
        assert all(w.code == ANGLE_REPEATED for w in result.warnings)


# --- Property 28 (task 24.6): Variant_Angles in the Copywriter message ---------------
import json  # noqa: E402

from services.adset_diversity import (  # noqa: E402
    VARIANT_ANGLES_BLOCK,
    build_copy_message,
    build_image_prompt_message,
)

_CTX_JSON = json.dumps({"adset": {"id": 7, "name": "ctx"}})


def _line_json(message: str, prefix: str):
    lines = [ln for ln in message.split("\n") if ln.startswith(prefix)]
    assert len(lines) == 1, f"expected one {prefix!r} line, got {len(lines)}"
    return json.loads(lines[0][len(prefix):])


@st.composite
def plan_and_subset(draw):
    ad_id = draw(st.integers(min_value=1, max_value=10**6))
    plan_id = f"plan_ad_{ad_id}"
    ad_slot = draw(st.integers(min_value=0, max_value=20))
    n = draw(st.integers(min_value=1, max_value=2 * SIZE + 1))
    templates = draw(st.lists(st.text(min_size=1), min_size=1, max_size=5, unique=True))
    slots = build_variant_slots(plan_id, ad_slot, n, templates)
    plan = {"id": plan_id, "concept": draw(st.text()), "ad_slot": ad_slot,
            "variants": [dict(s) for s in slots],
            "_project_templates": list(templates)}
    idx = sorted(draw(st.sets(st.integers(min_value=0, max_value=n - 1), min_size=1)))
    return ad_id, plan, [dict(plan["variants"][i]) for i in idx], idx


# Feature: adset-creative-diversity, Property 28: Variant_Angles en el mensaje al Copywriter
@settings(max_examples=100, deadline=None)
@given(data=plan_and_subset(),
       forbidden=st.lists(st.text(min_size=1), max_size=3))
def test_copy_message_carries_angles_of_subset_only(data, forbidden):
    """**Validates: Requirements 5.1, 14.6, 12.26**"""
    ad_id, plan, subset, idx = data
    snapshot = copy.deepcopy((plan, subset))
    msg = build_copy_message(plan, subset, forbidden, _CTX_JSON,
                             id_adset=7, ad_id=ad_id, project_id="proj")
    assert (plan, subset) == snapshot  # inputs not mutated

    # Exactly one {variant_key, template_id, angle} per slot of the subset, in order.
    payload = _line_json(msg, "Variant_Slots: ")
    assert payload == [{"variant_key": s["variant_key"], "template_id": s["template_id"],
                        "angle": s["angle"]} for s in subset]
    assert all(set(item) == {"variant_key", "template_id", "angle"} for item in payload)

    # No excluded slot (variant_key or its paired angle) in the Variant_Slots line.
    sent_keys = {item["variant_key"] for item in payload}
    excluded = [s for i, s in enumerate(plan["variants"]) if i not in set(idx)]
    for s in excluded:
        assert s["variant_key"] not in sent_keys
        assert {"variant_key": s["variant_key"], "template_id": s["template_id"],
                "angle": s["angle"]} not in payload

    # The VARIANT ANGLES block with the plan precedence, before the identity contract.
    assert VARIANT_ANGLES_BLOCK in msg
    assert msg.index(VARIANT_ANGLES_BLOCK) < msg.index("OUTPUT IDENTITY")
    assert "following the angle of ITS Variant_Slot" in VARIANT_ANGLES_BLOCK
    assert "refines WITHIN the Creative_Plan" in VARIANT_ANGLES_BLOCK
    assert "the plan wins" in VARIANT_ANGLES_BLOCK
    assert "Never leave the plan" in VARIANT_ANGLES_BLOCK
    assert "never touch any\nForbidden_Territory" in VARIANT_ANGLES_BLOCK
    assert "Do NOT copy `angle` into your output" in VARIANT_ANGLES_BLOCK

    # Forbidden_Territories still travel in the message.
    assert _line_json(msg, "Forbidden_Territories: ") == list(forbidden)


# Feature: adset-creative-diversity, Property 28: Variant_Angles en el mensaje al Copywriter
@settings(max_examples=100, deadline=None)
@given(data=plan_and_subset(), headline=st.text())
def test_image_prompt_message_has_no_angle(data, headline):
    """**Validates: Requirements 14.6, 12.26**"""
    ad_id, plan, subset, _ = data
    copies = [{"plan_id": plan["id"], "variant_key": s["variant_key"],
               "template_id": s["template_id"], "headline": [headline],
               "primary_text": ["p"]} for s in subset]
    no_angle = [{k: v for k, v in s.items() if k != "angle"} for s in subset]
    plan_no_angle = {**plan, "variants": [{k: v for k, v in s.items() if k != "angle"}
                                          for s in plan["variants"]]}
    msg = build_image_prompt_message(plan, subset, copies, _CTX_JSON,
                                     id_adset=7, ad_id=ad_id)
    assert '"angle"' not in msg
    assert VARIANT_ANGLES_BLOCK not in msg
    assert msg == build_image_prompt_message(plan_no_angle, no_angle, copies, _CTX_JSON,
                                             id_adset=7, ad_id=ad_id)
    assert _line_json(msg, "Variant_Slots: ") == [
        {"variant_key": s["variant_key"], "template_id": s["template_id"]} for s in subset]


# --- Unit tests (task 25.4): Variant_Angle --------------------------------------------

from services.adset_diversity import ANGLE_KEYS  # noqa: E402

# Recorded once from sha256("plan_ad_101") % 6; must not depend on PYTHONHASHSEED.
FIXED_PLAN_ID = "plan_ad_101"
FIXED_OFFSET = 2


def test_angle_vocabulary_shape():
    """**Validates: Requirements 14.1, 14.9**"""
    vocab = [dict(a) for a in ANGLE_VOCABULARY]
    assert len(vocab) >= 5
    assert ANGLE_KEYS == ("hook", "headline_structure", "copy_length")
    assert all(set(a) == set(ANGLE_KEYS) for a in vocab)
    assert all(isinstance(v, str) and v.strip() for a in vocab for v in a.values())
    assert len({tuple(sorted(a.items())) for a in vocab}) == len(vocab)  # no duplicates
    assert len({a["hook"] for a in vocab}) == len(vocab)
    assert len({a["headline_structure"] for a in vocab}) == len(vocab)
    cycle = ("short", "medium", "long")
    assert [a["copy_length"] for a in vocab] == [cycle[i % 3] for i in range(len(vocab))]


def test_angle_offset_fixed_value():
    """sha256-based, so stable across processes. **Validates: Requirements 14.2**"""
    assert angle_offset(FIXED_PLAN_ID) == FIXED_OFFSET
    assert angle_offset(FIXED_PLAN_ID) == angle_offset(FIXED_PLAN_ID)


def test_build_variant_slots_angles():
    """**Validates: Requirements 14.1, 14.2, 12.25**"""
    templates = ["tpl_a", "tpl_b", "tpl_c"]
    for n in (2, 6, 13):
        slots = build_variant_slots(FIXED_PLAN_ID, 1, n, templates)
        angles = [s["angle"] for s in slots]
        assert angles == [dict(ANGLE_VOCABULARY[(FIXED_OFFSET + k) % SIZE]) for k in range(n)]
        assert [s["variant_key"] for s in slots] == [f"{FIXED_PLAN_ID}_v{k}"
                                                    for k in range(1, n + 1)]
        assert len({s["template_id"] for s in slots}) == 1
        if n <= SIZE:
            assert len({tuple(sorted(a.items())) for a in angles}) == n
        else:
            assert all(angles[k] == angles[k + SIZE] for k in range(n - SIZE))
    # n = 2 starts at the recorded offset.
    assert build_variant_slots(FIXED_PLAN_ID, 0, 2, templates)[0]["angle"] == \
        dict(ANGLE_VOCABULARY[FIXED_OFFSET])


def test_angles_independent_of_task_id():
    """**Validates: Requirements 14.2, 12.25**"""
    templates = ["tpl_a", "tpl_b", "tpl_c", "tpl_d"]
    a = build_variant_slots(FIXED_PLAN_ID, 0, 4, template_order(templates, "task-1"))
    b = build_variant_slots(FIXED_PLAN_ID, 0, 4, template_order(templates, "task-2"))
    assert [s["angle"] for s in a] == [s["angle"] for s in b]
    assert [s["variant_key"] for s in a] == [s["variant_key"] for s in b]


def test_ensure_variant_angles_checkpoint_without_angle():
    """Legacy checkpoint (no ``angle``) → recomputed. **Validates: Requirements 14.5**"""
    plan = {"id": FIXED_PLAN_ID, "concept": "c", "ad_slot": 0,
            "variants": [{"variant_key": f"{FIXED_PLAN_ID}_v{k}", "template_id": "tpl_a"}
                         for k in (1, 2, 3)]}
    snapshot = copy.deepcopy(plan)
    fixed, recomputed = ensure_variant_angles(plan)
    assert recomputed is True
    assert plan == snapshot
    assert [s["angle"] for s in fixed["variants"]] == assign_variant_angles(FIXED_PLAN_ID, 3)
    assert [s["variant_key"] for s in fixed["variants"]] == \
        [s["variant_key"] for s in snapshot["variants"]]
    assert all(s["template_id"] == "tpl_a" for s in fixed["variants"])


def _angle_plan(angles: list) -> dict:
    return _plan(FIXED_PLAN_ID, angles)


def test_check_variant_angles_missing():
    """**Validates: Requirements 6.13**"""
    plan = _angle_plan([dict(ANGLE_VOCABULARY[0]), "__missing__"])
    result = check_variant_angles(plan, 2)
    assert _codes(result.errors) == [(ANGLE_MISSING, (f"{FIXED_PLAN_ID}_v2",))]
    assert result.warnings == ()
    assert repr(FIXED_PLAN_ID) in result.errors[0].message


def test_check_variant_angles_foreign():
    """**Validates: Requirements 6.13**"""
    foreign = {"hook": "question", "headline_structure": "contrast", "copy_length": "short"}
    plan = _angle_plan([foreign, dict(ANGLE_VOCABULARY[1])])
    result = check_variant_angles(plan, 2)
    assert _codes(result.errors) == [(ANGLE_NOT_IN_VOCABULARY, (f"{FIXED_PLAN_ID}_v1",))]
    assert result.warnings == ()


def test_check_variant_angles_repeated_is_error_up_to_vocabulary_size():
    """**Validates: Requirements 6.13**"""
    angles = [dict(a) for a in ANGLE_VOCABULARY]
    angles[-1] = dict(ANGLE_VOCABULARY[0])  # n = 6, slot 6 repeats slot 1
    result = check_variant_angles(_angle_plan(angles), len(angles))
    assert _codes(result.errors) == [
        (ANGLE_REPEATED, (f"{FIXED_PLAN_ID}_v1", f"{FIXED_PLAN_ID}_v{len(angles)}"))]
    assert result.warnings == ()


def test_check_variant_angles_repeated_is_warning_when_exhausted():
    """**Validates: Requirements 6.13**"""
    n = SIZE + 1  # 7
    angles = [dict(ANGLE_VOCABULARY[k % SIZE]) for k in range(n)]
    result = check_variant_angles(_angle_plan(angles), n)
    assert result.errors == ()
    assert _codes(result.warnings) == [
        (ANGLE_REPEATED, (f"{FIXED_PLAN_ID}_v1", f"{FIXED_PLAN_ID}_v{n}"))]


def _fixed_plan(n: int) -> dict:
    slots = build_variant_slots(FIXED_PLAN_ID, 0, n, ["tpl_a", "tpl_b"])
    return {"id": FIXED_PLAN_ID, "concept": "c", "ad_slot": 0,
            "variants": [dict(s) for s in slots], "_project_templates": ["tpl_a", "tpl_b"]}


def test_copy_message_initial_carries_all_angles():
    """**Validates: Requirements 14.6, 12.26**"""
    plan = _fixed_plan(3)
    msg = build_copy_message(plan, plan["variants"], ["other"], _CTX_JSON,
                             id_adset=7, ad_id=101, project_id="proj")
    assert VARIANT_ANGLES_BLOCK in msg
    assert _line_json(msg, "Variant_Slots: ") == [
        {"variant_key": s["variant_key"], "template_id": s["template_id"], "angle": s["angle"]}
        for s in plan["variants"]]


def test_copy_message_regeneration_carries_only_regenerated_angles():
    """**Validates: Requirements 14.6, 12.26**"""
    plan = _fixed_plan(3)
    subset = [plan["variants"][1]]
    msg = build_copy_message(plan, subset, [], _CTX_JSON,
                             id_adset=7, ad_id=101, project_id="proj")
    payload = _line_json(msg, "Variant_Slots: ")
    assert payload == [{"variant_key": f"{FIXED_PLAN_ID}_v2", "template_id": "tpl_a",
                        "angle": plan["variants"][1]["angle"]}]
    assert f"{FIXED_PLAN_ID}_v1" not in json.dumps(payload)
    assert f"{FIXED_PLAN_ID}_v3" not in json.dumps(payload)


def test_image_prompt_message_without_angle():
    """**Validates: Requirements 14.6, 12.26**"""
    plan = _fixed_plan(2)
    copies = [{"plan_id": FIXED_PLAN_ID, "variant_key": s["variant_key"],
               "template_id": s["template_id"], "headline": ["h"], "primary_text": ["p"]}
              for s in plan["variants"]]
    msg = build_image_prompt_message(plan, plan["variants"], copies, _CTX_JSON,
                                     id_adset=7, ad_id=101)
    assert '"angle"' not in msg
    assert VARIANT_ANGLES_BLOCK not in msg
    assert _line_json(msg, "Variant_Slots: ") == [
        {"variant_key": s["variant_key"], "template_id": s["template_id"]}
        for s in plan["variants"]]


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
