"""Unit tests for services/adset_diversity.py (adset-creative-diversity, Req 3.1, 4.5, 4.9,
4.10, 4.11, 12.19, 12.20).

Examples of Ad_Slot resolution (mock and real Adset_Context shapes), Variant_Slots with
``n_variants=6`` over the 3 templates of ``_MOCK_TEMPLATES``, the Creative_Plan and the
agent messages built from a sanitised (``_strip_signed_urls``) Adset_Context.
No network, Redis or LLM.

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity.py
    PYTHONPATH=. python -m tests.test_adset_diversity
"""
import copy
import hashlib
import json
import random

import pytest

from services.adset_diversity import (
    FULL_ADSET_CONTEXT_HEADER,
    ad_template_for_slot,
    bind_territories,
    build_copy_message,
    build_creative_plan,
    build_estratega_message,
    build_image_prompt_message,
    build_validador_message,
    build_variant_proposals,
    build_variant_slots,
    extract_adset_ads,
    check_variant_items,
    first_text,
    normalize_variant_fields,
    repair_variant_items,
    resolve_ad_slots,
    resolve_project_templates,
    slot_ad_templates,
    template_order,
    template_seed,
)
from services.diversity_checker import check_variant_slots
from services.job_runner_service import _strip_signed_urls
from services.territory_assignment import assign_territories, unwrap_adset
from tests._diversity_pipeline_fakes import (
    LogCapture,
    make_adset_context,
    mock_template_ids,
    mock_templates,
)

TASK_ID = "task-diversity-unit"
ID_ADSET = 7
PROJECT_ID = "test-project-id"
SIGNED_URL = (
    "https://bucket.s3.amazonaws.com/brand/logo.png"
    "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAFAKE%2F20250101"
    "&X-Amz-Signature=deadbeef"
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _real_context(ad_ids) -> dict:
    """Real (single-wrapped) shape: ``{"ok": True, "adset": {...}}``."""
    mock = make_adset_context(ad_ids)
    return {"ok": True, "adset": copy.deepcopy(unwrap_adset(mock))}


def _territories(ctx: dict, slot_ad_ids: list[int]):
    raw = assign_territories(ctx, n_ads=len(slot_ad_ids), adset_id=ID_ADSET, n_variantes=1)
    return bind_territories(raw, slot_ad_ids)


def _sanitised_context(ad_ids=(101, 102)) -> tuple[dict, str]:
    ctx = make_adset_context(ad_ids)
    unwrap_adset(ctx)["logo_url"] = SIGNED_URL
    clean = _strip_signed_urls(ctx)
    return clean, json.dumps(clean, ensure_ascii=False)


def _plan_for(ctx: dict, slot_ad_ids: list[int], slot: int, n_variants: int = 3):
    territories = _territories(ctx, slot_ad_ids)
    ad_id = slot_ad_ids[slot]
    slots = build_variant_slots(f"plan_ad_{ad_id}", slot, n_variants, mock_template_ids())
    return territories, build_creative_plan(territories[slot], ad_id, slot, slots)


# ---------------------------------------------------------------------------
# Ad_Slots (Req 3.1, 3.2, 3.5–3.7)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("shape", ["mock", "real"])
def test_extract_adset_ads_mock_and_real_shapes(shape):
    entries = [103, 101, 0, -4, True, "x", None, 101, 102]
    ctx = make_adset_context(entries) if shape == "mock" else _real_context(entries)
    with LogCapture(level="WARNING") as cap:
        assert extract_adset_ads(ctx, TASK_ID) == [101, 102, 103]
    discarded = [line for line in cap.lines if line.startswith(f"[{TASK_ID}]")]
    # 0, -4, True, "x", None (invalid) + the repeated 101
    assert len(discarded) == 6


def test_extract_adset_ads_without_ads_returns_empty():
    ctx = make_adset_context([])
    assert extract_adset_ads(ctx, TASK_ID) == []
    unwrap_adset(ctx).pop("ads")
    assert extract_adset_ads(ctx, TASK_ID) == []


def test_resolve_ad_slots_scenarios():
    ids = [101, 102, 103]
    s1 = resolve_ad_slots(ids, None, TASK_ID)
    assert (s1.slot_ad_ids, s1.target_ad_ids, s1.extra_slot) == (ids, ids, False)
    assert resolve_ad_slots(ids, 0, TASK_ID).target_ad_ids == ids

    s2 = resolve_ad_slots(ids, 102, TASK_ID)
    assert (s2.slot_ad_ids, s2.target_ad_ids, s2.extra_slot) == (ids, [102], False)

    with LogCapture(level="WARNING") as cap:
        s2_extra = resolve_ad_slots(ids, 999, TASK_ID)
    assert (s2_extra.slot_ad_ids, s2_extra.target_ad_ids, s2_extra.extra_slot) == (
        [101, 102, 103, 999], [999], True)
    assert any(f"[{TASK_ID}]" in line and "999" in line for line in cap.lines)
    assert ids == [101, 102, 103]  # input not mutated


def test_bind_territories_sets_ad_id_per_slot_and_checks_length():
    ctx = make_adset_context([101, 102])
    raw = assign_territories(ctx, n_ads=2, adset_id=ID_ADSET, n_variantes=1)
    bound = bind_territories(raw, [101, 102])
    assert [t.ad_id for t in bound] == [101, 102]
    assert [t.territory for t in bound] == [t.territory for t in raw]
    assert bound[0] is not raw[0]
    with pytest.raises(ValueError):
        bind_territories(raw, [101])


# ---------------------------------------------------------------------------
# Project_Templates and Variant_Slots (Req 4.5, 4.6, 4.9, 12.19)
# ---------------------------------------------------------------------------

def test_resolve_project_templates_from_mock_templates():
    assert resolve_project_templates(mock_templates()) == mock_template_ids()
    assert len(mock_template_ids()) == 3


def test_resolve_project_templates_edge_cases():
    assert resolve_project_templates({"ok": False, "templates": [{"id": "a"}]}) == []
    assert resolve_project_templates({"ok": True, "templates": "nope"}) == []
    assert resolve_project_templates(None) == []
    ctx = {"ok": True, "templates": [{"template_id": 5}, "x", {"name": "no id"}, {"id": "b"}]}
    assert resolve_project_templates(ctx) == ["5", "b"]


def test_resolve_project_templates_dedupes_first_occurrence_in_order():
    # Repeated ids (also int vs str, and id vs template_id) keep only the first one (Req 4.5, 4.7).
    ctx = {"ok": True, "templates": [
        {"id": "T2"}, {"id": "T1"}, {"id": "T2"}, {"template_id": "T1"},
        {"id": 3}, {"id": "3"}, {"id": "T4"},
    ]}
    assert resolve_project_templates(ctx) == ["T2", "T1", "3", "T4"]
    assert resolve_project_templates({"ok": True, "templates": [{"id": "T1"}, {"id": "T1"}]}) == ["T1"]


def test_resolve_project_templates_skips_invalid_entries():
    ctx = {"ok": True, "templates": [
        None, 7, "T0", ["T0"], {}, {"id": None}, {"id": ""}, {"template_id": ""},
        {"id": "", "template_id": "T5"}, {"name": "x"}, {"id": "T6"},
    ]}
    assert resolve_project_templates(ctx) == ["T5", "T6"]
    assert resolve_project_templates({"ok": True, "templates": [None, {}, {"id": ""}]}) == []
    assert resolve_project_templates({"ok": True}) == []


def test_resolve_project_templates_ok_false_returns_empty():
    templates = [{"id": "T1"}, {"id": "T2"}]
    assert resolve_project_templates({"ok": False, "templates": templates}) == []
    assert resolve_project_templates({"ok": False}) == []
    # ok missing is not False: templates are resolved
    assert resolve_project_templates({"templates": templates}) == ["T1", "T2"]


def test_ad_template_for_slot_rotation():
    templates = ["tA", "tB", "tC"]
    assert [ad_template_for_slot(s, templates) for s in range(7)] == [
        "tA", "tB", "tC", "tA", "tB", "tC", "tA"]
    assert ad_template_for_slot(5, ["only"]) == "only"


def test_ad_template_for_slot_rejects_empty_and_negative_slot():
    with pytest.raises(ValueError):
        ad_template_for_slot(0, [])
    with pytest.raises(ValueError):
        ad_template_for_slot(-1, ["tA", "tB"])


def test_slot_ad_templates_rotation_and_edge_cases():
    templates = ["tA", "tB", "tC"]
    assert slot_ad_templates(3, templates) == ["tA", "tB", "tC"]  # distinct while n <= len
    assert slot_ad_templates(5, templates) == ["tA", "tB", "tC", "tA", "tB"]
    assert slot_ad_templates(0, templates) == []
    assert slot_ad_templates(0, []) == []
    with pytest.raises(ValueError):
        slot_ad_templates(2, [])
    # Consistent with build_variant_slots: every variant of slot s uses slot_ad_templates[s]
    for s, expected in enumerate(slot_ad_templates(5, templates)):
        slots = build_variant_slots(f"plan_ad_{s}", s, 4, templates)
        assert {v["template_id"] for v in slots} == {expected}


@pytest.mark.parametrize("ad_slot", [0, 1, 2])
def test_variant_slots_n6_with_three_mock_templates(ad_slot):
    templates = mock_template_ids()
    plan_id = f"plan_ad_{100 + ad_slot}"
    slots = build_variant_slots(plan_id, ad_slot, 6, templates)
    assert [s["variant_key"] for s in slots] == [f"{plan_id}_v{k}" for k in range(1, 7)]
    # P11: every variant of the Ad uses the Ad_Template templates[ad_slot % 3] (Req 4.5, 4.6).
    assert [s["template_id"] for s in slots] == [templates[ad_slot % 3]] * 6
    plan = {"id": plan_id, "variants": slots, "_project_templates": templates}
    result = check_variant_slots(plan, templates, 6)
    assert result.ok
    assert result.errors == ()


# ---------------------------------------------------------------------------
# Template_Order (Decision P12, D18; Req 4.10, 4.11, 12.20)
# ---------------------------------------------------------------------------

def test_template_seed_fixed_value_independent_of_hash_salt():
    # Recorded value: sha256("adset-templates:<seed>")[:8] big-endian, never hash(),
    # so it is the same under any PYTHONHASHSEED, worker or restart.
    assert template_seed(TASK_ID) == 15791221628417371370
    assert template_seed("") == 10415473428265243216
    expected = int.from_bytes(
        hashlib.sha256(f"adset-templates:{TASK_ID}".encode("utf-8")).digest()[:8], "big")
    assert template_seed(TASK_ID) == expected
    assert 0 <= template_seed("任务-ñ") < 2 ** 64


def test_template_order_is_deterministic_permutation_of_mock_templates():
    templates = mock_template_ids()
    before = list(templates)
    state = random.getstate()

    order = template_order(templates, TASK_ID)

    assert order == template_order(templates, TASK_ID)  # same task_id -> same order
    assert sorted(order) == sorted(templates) and len(order) == 3
    assert order is not templates
    assert templates == before  # input not mutated
    assert random.getstate() == state  # global random untouched


def test_template_order_differs_between_two_task_ids():
    # Req 12.20 (f): two concrete task_ids yield different Template_Orders.
    templates = mock_template_ids()
    order_a = template_order(templates, "task-a")
    order_b = template_order(templates, "task-b")
    assert order_a != order_b
    assert sorted(order_a) == sorted(order_b) == sorted(templates)


def test_template_order_empty_and_single_element():
    assert template_order([], TASK_ID) == []
    single = ["only"]
    out = template_order(single, TASK_ID)
    assert out == ["only"]
    assert out is not single
    assert template_order(("x",), "") == ["x"]


def test_build_variant_slots_rejects_invalid_input():
    with pytest.raises(ValueError):
        build_variant_slots("plan_ad_1", 0, 3, [])
    with pytest.raises(ValueError):
        build_variant_slots("plan_ad_1", 0, 0, ["a"])


def test_build_variant_slots_adds_angle_and_creative_plan_keeps_it():
    # P14, D22 (Req 14.1, 14.4): slot k carries assign_variant_angles(plan_id, n)[k - 1];
    # template_id is unchanged (D15) and build_creative_plan does not drop the angle.
    from services.adset_diversity import assign_variant_angles

    templates = mock_template_ids()
    plan_id = "plan_ad_42"
    slots = build_variant_slots(plan_id, 1, 4, templates)
    assert [s["angle"] for s in slots] == assign_variant_angles(plan_id, 4)
    assert [s["template_id"] for s in slots] == [templates[1]] * 4

    _, plan = _plan_for(make_adset_context((101, 102)), [101, 102], 1, n_variants=4)
    assert plan["variants"] == build_variant_slots("plan_ad_102", 1, 4, templates)
    assert [v["angle"] for v in plan["variants"]] == assign_variant_angles("plan_ad_102", 4)


# ---------------------------------------------------------------------------
# Creative_Plan (Req 4.1, 4.3, 4.9)
# ---------------------------------------------------------------------------

def test_creative_plan_keeps_territory_and_has_six_variants():
    ctx = make_adset_context([101, 102])
    territories, plan = _plan_for(ctx, [101, 102], slot=1, n_variants=6)
    territory = territories[1]

    assert plan["id"] == "plan_ad_102"
    assert "template_id" not in plan and "template_selection_reason" not in plan
    assert len(plan["variants"]) == 6
    assert plan["target_insight"] == territory.territory.anchor_primary.text
    assert plan["color_palette"] == territory.territory.palette_family
    assert plan["emocion"] == territory.territory.axes.emocion
    assert plan["_territory"]["territorio_prohibido"] == territory.territorio_prohibido
    assert plan["_territory"]["territorio_prohibido"] == [
        territories[0].territory.anchor_primary.text
    ]


def test_first_text():
    assert first_text(["a", "b"]) == "a"
    assert first_text("x") == "x"
    assert first_text([]) == ""
    assert first_text(None) == ""
    assert first_text([3]) == ""


def test_build_variant_proposals_one_per_slot():
    ctx = make_adset_context([101])
    _, plan = _plan_for(ctx, [101], slot=0, n_variants=6)
    keys = [s["variant_key"] for s in plan["variants"]]
    copies = [{"variant_key": k, "headline": f"h{k}"} for k in reversed(keys)]
    prompts = [{"variant_key": k, "image_prompts": [f"p{k}"]} for k in keys]
    proposals = build_variant_proposals(plan, copies, prompts, 101)
    assert [p["variant_key"] for p in proposals] == keys
    assert all(p["copy"]["headline"] == f"h{p['variant_key']}" for p in proposals)
    assert all(p["image_prompts"] == [f"p{p['variant_key']}"] for p in proposals)


# ---------------------------------------------------------------------------
# Messages with sanitised context (Req 2.5, 4.2, 5.1, 5.7, 7.3)
# ---------------------------------------------------------------------------

def _assert_context_block(message: str, ctx_json: str) -> None:
    assert f"{FULL_ADSET_CONTEXT_HEADER}\n{ctx_json}\n" in message
    assert "X-Amz-" not in message
    assert "https://bucket.s3.amazonaws.com/brand/logo.png" in message


def test_messages_carry_sanitised_full_adset_context():
    ctx, ctx_json = _sanitised_context()
    assert "X-Amz-" not in ctx_json
    territories, plan = _plan_for(ctx, [101, 102], slot=0, n_variants=6)
    slots = plan["variants"]
    forbidden = plan["_territory"]["territorio_prohibido"]

    estratega = build_estratega_message(ctx, ctx_json, territories[0])
    _assert_context_block(estratega, ctx_json)
    assert territories[0].territory.anchor_primary.text in estratega

    copy_msg = build_copy_message(plan, slots, forbidden, ctx_json,
                                  id_adset=ID_ADSET, ad_id=101, project_id=PROJECT_ID)
    _assert_context_block(copy_msg, ctx_json)
    assert "exactly 6 copy object(s)" in copy_msg
    assert all(s["variant_key"] in copy_msg and s["template_id"] in copy_msg for s in slots)
    assert f"Forbidden_Territories: {json.dumps(forbidden, ensure_ascii=False)}" in copy_msg

    copies = [{"variant_key": s["variant_key"], "headline": "h"} for s in slots[:2]]
    copies.append({"variant_key": "other_v1", "headline": "foreign"})
    prompt_msg = build_image_prompt_message(plan, slots[:2], copies, ctx_json,
                                            id_adset=ID_ADSET, ad_id=101)
    _assert_context_block(prompt_msg, ctx_json)
    assert "exactly 2 object(s)" in prompt_msg
    assert "foreign" not in prompt_msg

    proposals = build_variant_proposals(plan, [], [], 101)
    validador = build_validador_message(plan, proposals, forbidden, ctx_json, ["err one"])
    _assert_context_block(validador, ctx_json)
    assert 'id="plan_ad_101"' in validador
    assert json.dumps([s["variant_key"] for s in slots]) in validador
    # D21: informative warnings, the plan once (without variants) and the Validador_Views.
    assert ("Deterministic diversity warnings (this iteration, informative only):\n"
            "- err one\n") in validador
    assert "Deterministic diversity errors" not in validador
    assert "Proposals:" not in validador
    plan_lines = [l for l in validador.split("\n") if l.startswith("Plan: ")]
    assert len(plan_lines) == 1
    plan_payload = json.loads(plan_lines[0][len("Plan: "):])
    assert plan_payload["id"] == "plan_ad_101"
    assert "variants" not in plan_payload and "_project_templates" not in plan_payload
    variant_lines = [l for l in validador.split("\n") if l.startswith("Variants: ")]
    assert len(variant_lines) == 1
    views = json.loads(variant_lines[0][len("Variants: "):])
    assert [v["variant_key"] for v in views] == [s["variant_key"] for s in slots]
    assert [v["angle"] for v in views] == [s["angle"] for s in slots]
    assert all(v["copy"] == {} and v["image_prompts"] == [] for v in views)
    assert all(marker in validador for marker in ("(a)", "(b)", "(c)"))


def test_messages_are_deterministic_and_default_empty_context():
    ctx, ctx_json = _sanitised_context()
    _, plan = _plan_for(ctx, [101, 102], slot=1)
    args = (plan, plan["variants"], ["x"], ctx_json)
    kwargs = dict(id_adset=ID_ADSET, ad_id=102, project_id=PROJECT_ID)
    assert build_copy_message(*args, **kwargs) == build_copy_message(*args, **kwargs)
    validador = build_validador_message(plan, [], [], "", [])
    assert f"{FULL_ADSET_CONTEXT_HEADER}\n{{}}\n" in validador
    assert ("Deterministic diversity warnings (this iteration, informative only):\n"
            "- none\n") in validador


# ---------------------------------------------------------------------------
# repair_variant_items (production regression, job 0930d359)
# ---------------------------------------------------------------------------

def _repair_slots(templates, n):
    return build_variant_slots("plan_ad_827", 0, n, templates)


def _identity(items):
    return [(i.get("plan_id"), i.get("variant_key"), i.get("template_id")) for i in items]


def test_repair_variant_key_written_into_plan_id():
    slots = _repair_slots(["t1", "t2", "t3"], 3)
    items = [{"plan_id": s["variant_key"], "template_id": s["template_id"], "headline": ["h"]}
             for s in slots]
    before = copy.deepcopy(items)
    repaired, messages = repair_variant_items(items, slots, "plan_ad_827")
    assert _identity(repaired) == [("plan_ad_827", s["variant_key"], s["template_id"]) for s in slots]
    assert len(messages) == 3 and all("plan_id" in m for m in messages)
    assert items == before  # input not mutated
    assert check_variant_items(repaired, slots, "plan_ad_827", kind="copy") == []


def test_repair_missing_variant_key_by_template_in_slot_order():
    # 4 variants over 2 templates: repeated templates are assigned in slot order.
    slots = _repair_slots(["t1", "t2"], 4)
    items = [{"plan_id": "plan_ad_827", "template_id": s["template_id"]} for s in slots]
    repaired, _ = repair_variant_items(items, slots, "plan_ad_827")
    assert [i["variant_key"] for i in repaired] == [s["variant_key"] for s in slots]
    assert check_variant_items(repaired, slots, "plan_ad_827", kind="image_prompt") == []


def test_repair_respects_explicit_keys_and_never_crosses_templates():
    slots = _repair_slots(["t1", "t2", "t3"], 3)
    items = [
        {"plan_id": "plan_ad_827", "variant_key": slots[1]["variant_key"], "template_id": "t2"},
        {"plan_id": "plan_ad_827", "template_id": "t2"},   # t2 already taken → unresolved
        {"plan_id": "plan_ad_827", "template_id": "tZ"},   # unknown template → unresolved
        {"template_id": "t1"},                             # no plan_id → resolved + plan_id
    ]
    repaired, _ = repair_variant_items(items, slots, "plan_ad_827")
    assert repaired[0]["variant_key"] == slots[1]["variant_key"]
    assert "variant_key" not in repaired[1] and "variant_key" not in repaired[2]
    assert (repaired[3]["plan_id"], repaired[3]["variant_key"]) == ("plan_ad_827", slots[0]["variant_key"])
    # Still invalid: the strict check rejects what could not be resolved safely.
    assert check_variant_items(repaired, slots, "plan_ad_827", kind="copy")


def test_repair_non_list_and_unknown_keys_untouched():
    slots = _repair_slots(["t1"], 1)
    assert repair_variant_items(None, slots, "plan_ad_827") == (None, [])
    items = [{"plan_id": "x", "variant_key": "other_v1", "template_id": "t1"}]
    assert repair_variant_items(items, slots, "plan_ad_827") == (items, [])


def test_normalize_scalar_list_fields_job_259a13a7():
    """ad=828: the Copywriter answered headline/primary_text/description/cta as strings."""
    items = [{"plan_id": "plan_ad_828", "headline": "H", "primary_text": "P",
              "description": "D", "cta": "LEARN_MORE", "template_elements": {"element_id": "t"}}]
    out, messages = normalize_variant_fields("```json\n" + json.dumps(items) + "\n```", kind="copy")
    parsed = json.loads(out)[0]
    assert parsed["headline"] == ["H"] and parsed["cta"] == ["LEARN_MORE"]
    assert parsed["template_elements"] == [{"element_id": "t"}]
    assert len(messages) == 5


@pytest.mark.parametrize("response", ["", "not json", "[]", '[{"headline": ["ok"], "cta": ""}]'])
def test_normalize_leaves_other_answers_untouched(response):
    assert normalize_variant_fields(response, kind="copy") == (response, [])


def test_variant_validator_accepts_scalar_copy_fields():
    from services.ads_validators import validate_copywriter_response
    from services.adset_diversity import make_variant_validator

    slots = build_variant_slots("plan_ad_828", 1, 2, ["t1", "t2"])
    items = [{"plan_id": "plan_ad_828", "variant_key": s["variant_key"], "template_id": s["template_id"],
              "headline": f"H{i}", "primary_text": "P", "description": "D", "cta": "LEARN_MORE",
              "template_elements": [{"element_id": "t", "text": "x"}]}
             for i, s in enumerate(slots)]
    result = make_variant_validator(validate_copywriter_response, slots, "plan_ad_828",
                                    kind="copy")(json.dumps(items))
    assert result.is_valid, result.errors
    assert [c["headline"] for c in result.data] == [["H0"], ["H1"]]


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
