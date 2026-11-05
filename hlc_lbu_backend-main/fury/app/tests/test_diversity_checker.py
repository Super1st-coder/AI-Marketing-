"""Unit tests for services/diversity_checker.py (adset-creative-diversity, Req 6.2–6.10, 12.7).

One passing case and one failing case per rule 6.2–6.10, exhaustion warnings and D6.

Run with:
    PYTHONPATH=. pytest tests/test_diversity_checker.py
    PYTHONPATH=. python -m tests.test_diversity_checker
"""
import copy

from schemas.territory_schemas import AdDescription, Anchor, StyleAxes, Territory
from services.adset_diversity import slot_ad_templates
from services.diversity_checker import (
    AD_TEMPLATE_REPEATED,
    ANCHOR_REPEATED,
    AXIS_REPEATED,
    COPY_REPEATED,
    COUNT_MISMATCH,
    FORBIDDEN_IS_OWN_ANCHOR,
    FORBIDDEN_TERRITORY,
    PALETTE_REPEATED,
    PLAN_ID_MISMATCH,
    TEMPLATE_MIXED_IN_AD,
    TEMPLATE_NOT_IN_PROJECT,
    check_ad_templates,
    check_territories,
    check_variant_slots,
    check_variants,
)
from services.territory_assignment import AXIS_VOCAB, PALETTE_FAMILIES

TEMPLATES = ["tpl_a", "tpl_b", "tpl_c"]
PLAN_ID = "plan_ad_101"
OWN_ANCHOR = "envio gratis"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def _ad(slot: int, text: str, category: str = "features", axes=None, palette=None) -> AdDescription:
    """Ad_Territory for ``slot``; axes/palette default to distinct per-slot values."""
    if axes is None:
        axes = {ax: vocab[slot % len(vocab)] for ax, vocab in AXIS_VOCAB.items()}
    if palette is None:
        palette = PALETTE_FAMILIES[slot % len(PALETTE_FAMILIES)]
    return AdDescription(
        ad_id=100 + slot,
        adset_id=7,
        territory=Territory(
            anchor_primary=Anchor(category=category, text=text),
            axes=StyleAxes(**axes),
            palette_family=palette,
        ),
    )


def _plan(n: int = 3, template: str = TEMPLATES[0]) -> dict:
    """Creative_Plan of one Ad with ``n`` variants sharing one Ad_Template (P11)."""
    return {
        "id": PLAN_ID,
        "target_insight": OWN_ANCHOR,
        "_territory": {"anchor_primary": {"category": "features", "text": OWN_ANCHOR}},
        "variants": [
            {"variant_key": f"{PLAN_ID}_v{k}", "template_id": template}
            for k in range(1, n + 1)
        ],
    }


def _copies(plan: dict) -> list[dict]:
    return [
        {
            "variant_key": s["variant_key"],
            "plan_id": plan["id"],
            "template_id": s["template_id"],
            "headline": [f"Titular {i}"],
            "primary_text": [f"Texto principal {i}"],
        }
        for i, s in enumerate(plan["variants"])
    ]


def _prompts(plan: dict) -> list[dict]:
    return [
        {
            "variant_key": s["variant_key"],
            "plan_id": plan["id"],
            "template_id": s["template_id"],
            "image_prompt": f"prompt {i}",
        }
        for i, s in enumerate(plan["variants"])
    ]


def _check(plan, copies=None, prompts=None, n=3, forbidden=(), templates=TEMPLATES):
    return check_variants(
        plan,
        _copies(plan) if copies is None else copies,
        _prompts(plan) if prompts is None else prompts,
        project_templates=templates,
        n_variants=n,
        forbidden=list(forbidden),
    )


def _codes(issues) -> list[str]:
    return [i.code for i in issues]


# ---------------------------------------------------------------------------
# Req 6.2 — anchor_primary.text
# ---------------------------------------------------------------------------
def test_6_2_distinct_anchors_pass():
    res = check_territories([_ad(0, "a"), _ad(1, "b")], product_pool_size=2, buyer_pool_size=0)
    assert res.errors == () and res.warnings == ()


def test_6_2_repeated_anchor_within_pool_is_error():
    res = check_territories([_ad(0, "a"), _ad(1, "a")], product_pool_size=2, buyer_pool_size=0)
    assert _codes(res.errors) == [ANCHOR_REPEATED]
    assert res.errors[0].ad_slots == (0, 1)
    assert "Ad_Slots 0 and 1" in res.errors[0].message and "'a'" in res.errors[0].message
    assert res.warnings == ()


# ---------------------------------------------------------------------------
# Req 6.3 — axes and palette_family
# ---------------------------------------------------------------------------
def test_6_3_distinct_axes_and_palette_pass():
    ads = [_ad(s, f"t{s}") for s in range(5)]
    res = check_territories(ads, product_pool_size=5, buyer_pool_size=0)
    assert res.errors == () and res.warnings == ()


def test_6_3_repeated_axis_within_vocab_is_error():
    axes = {ax: vocab[0] for ax, vocab in AXIS_VOCAB.items()}
    ads = [_ad(0, "a", axes=axes), _ad(1, "b", axes={**axes, "intencion": AXIS_VOCAB["intencion"][1],
                                                     "visual_dominante": AXIS_VOCAB["visual_dominante"][1],
                                                     "contexto_uso": AXIS_VOCAB["contexto_uso"][1],
                                                     "psicologia": AXIS_VOCAB["psicologia"][1]})]
    res = check_territories(ads, product_pool_size=2, buyer_pool_size=0)
    assert _codes(res.errors) == [AXIS_REPEATED]
    msg = res.errors[0].message
    assert "Ad_Slots 0 and 1" in msg and "emocion" in msg and repr(AXIS_VOCAB["emocion"][0]) in msg


def test_6_3_repeated_palette_within_vocab_is_error():
    ads = [_ad(0, "a", palette="calido"), _ad(1, "b", palette="calido")]
    res = check_territories(ads, product_pool_size=2, buyer_pool_size=0)
    assert _codes(res.errors) == [PALETTE_REPEATED]
    assert "palette_family" in res.errors[0].message and "'calido'" in res.errors[0].message


def test_6_3_missing_axis_values_not_compared():
    empty = {ax: None for ax in AXIS_VOCAB}
    ads = [_ad(0, "a", axes=empty, palette=None), _ad(1, "b", axes=empty, palette=None)]
    # palette None → _ad assigns a default; override after construction.
    for ad in ads:
        ad.territory.palette_family = None
    res = check_territories(ads, product_pool_size=2, buyer_pool_size=0)
    assert res.errors == () and res.warnings == ()


# ---------------------------------------------------------------------------
# Req 6.10 — exhaustion → warning instead of error
# ---------------------------------------------------------------------------
def test_6_10_anchor_repeat_with_exhausted_pool_is_warning():
    res = check_territories([_ad(0, "a"), _ad(1, "a")], product_pool_size=1, buyer_pool_size=5)
    assert res.errors == ()
    assert _codes(res.warnings) == [ANCHOR_REPEATED]
    assert "exhausted" in res.warnings[0].message


def test_6_10_anchor_repeat_across_sides_exhausted_only_one_side_is_error():
    # product side exhausted (1 slot > 0 pool) but buyer side is not (1 slot <= 3 pool).
    ads = [_ad(0, "a", category="features"), _ad(1, "a", category="pain_points")]
    res = check_territories(ads, product_pool_size=0, buyer_pool_size=3)
    assert _codes(res.errors) == [ANCHOR_REPEATED]
    assert res.warnings == ()


def test_6_10_axis_repeat_with_exhausted_vocab_is_warning():
    # 6 slots > 5 values of "intencion" → slot 0 and 5 repeat it as a warning.
    # emocion and palette have 6 values → no repeat with 6 slots.
    ads = [_ad(s, f"t{s}") for s in range(6)]
    res = check_territories(ads, product_pool_size=6, buyer_pool_size=0)
    assert res.errors == ()
    assert _codes(res.warnings) == [AXIS_REPEATED] * 4
    assert all(w.ad_slots == (0, 5) for w in res.warnings)


def test_6_10_palette_repeat_with_exhausted_vocab_is_warning():
    ads = [_ad(s, f"t{s}") for s in range(7)]  # slot 6 reuses palette/emocion of slot 0
    res = check_territories(ads, product_pool_size=7, buyer_pool_size=0)
    assert res.errors == ()
    assert PALETTE_REPEATED in _codes(res.warnings)


# ---------------------------------------------------------------------------
# Req 6.4 — plan_id
# ---------------------------------------------------------------------------
def test_6_4_conforming_variants_pass():
    res = _check(_plan())
    assert res.errors == () and res.warnings == ()


def test_6_4_wrong_plan_id_is_error():
    plan = _plan()
    copies = _copies(plan)
    copies[1]["plan_id"] = "plan_ad_999"
    res = _check(plan, copies=copies)
    assert _codes(res.errors) == [PLAN_ID_MISMATCH]
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v2",)


# ---------------------------------------------------------------------------
# Req 6.5 — counts
# ---------------------------------------------------------------------------
def test_6_5_matching_counts_pass():
    res = _check(_plan(n=2), n=2)
    assert _codes(res.errors) == []


def test_6_5_count_mismatch_copies_and_prompts():
    plan = _plan()
    res = _check(plan, copies=_copies(plan)[:2], prompts=_prompts(plan)[:1])
    assert _codes(res.errors) == [COUNT_MISMATCH, COUNT_MISMATCH]
    assert "expected 3 copies, got 2" in res.errors[0].message
    assert "expected 3 image prompts, got 1" in res.errors[1].message
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v3",)


# ---------------------------------------------------------------------------
# Req 6.6 — template_id in Project_Templates
# ---------------------------------------------------------------------------
def test_6_6_slots_and_variants_with_valid_templates_pass():
    plan = _plan()
    assert check_variant_slots(plan, TEMPLATES, 3).errors == ()
    assert _check(plan).errors == ()


def test_6_6_template_not_in_project_is_error():
    plan = _plan()
    bad_plan = copy.deepcopy(plan)
    for slot in bad_plan["variants"]:  # whole Ad on a foreign template → only 6.6
        slot["template_id"] = "tpl_x"
    res = check_variant_slots(bad_plan, TEMPLATES, 3)
    assert _codes(res.errors) == [TEMPLATE_NOT_IN_PROJECT] * 3
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v1",) and "'tpl_x'" in res.errors[0].message

    prompts = _prompts(plan)
    prompts[2]["template_id"] = "tpl_x"  # a single foreign prompt also breaks P11 (6.7)
    res = _check(plan, prompts=prompts)
    assert _codes(res.errors) == [TEMPLATE_NOT_IN_PROJECT, TEMPLATE_MIXED_IN_AD]
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v3",)
    assert res.errors[1].variant_keys == (f"{PLAN_ID}_v1", f"{PLAN_ID}_v3")


# ---------------------------------------------------------------------------
# Req 6.7 — one template per Ad (P11)
# ---------------------------------------------------------------------------
def test_6_7_same_template_for_all_variants_passes():
    plan = _plan(n=2)
    assert plan["variants"][1]["template_id"] == plan["variants"][0]["template_id"]
    res = check_variant_slots(plan, TEMPLATES, 2)
    assert res.errors == () and res.warnings == ()


def test_6_7_template_other_than_ad_template_is_error():
    plan = _plan(n=2)
    plan["variants"][1]["template_id"] = TEMPLATES[1]  # in Project_Templates, not the Ad's
    res = check_variant_slots(plan, TEMPLATES, 2)
    assert _codes(res.errors) == [TEMPLATE_MIXED_IN_AD]
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v1", f"{PLAN_ID}_v2")
    assert res.warnings == ()


def test_6_7_six_variants_with_one_template_pass():
    plan = _plan(n=6)  # 6 variants > 3 templates, all on the Ad_Template
    assert check_variant_slots(plan, TEMPLATES, 6).errors == ()
    res = _check(plan, n=6)
    assert res.errors == () and res.warnings == ()


# ---------------------------------------------------------------------------
# Req 6.8 — identical first headline + primary_text
# ---------------------------------------------------------------------------
def test_6_8_same_headline_different_text_passes():
    plan = _plan()
    copies = _copies(plan)
    copies[1]["headline"] = copies[0]["headline"]
    assert _check(plan, copies=copies).errors == ()


def test_6_8_identical_copy_normalized_is_error():
    plan = _plan()
    copies = _copies(plan)
    copies[2]["headline"] = "  TITULAR 0 "  # str, not list; case and spaces differ
    copies[2]["primary_text"] = ["texto PRINCIPAL 0", "otro"]
    res = _check(plan, copies=copies)
    assert _codes(res.errors) == [COPY_REPEATED]
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v1", f"{PLAN_ID}_v3")


# ---------------------------------------------------------------------------
# Req 6.9 — Forbidden_Territories
# ---------------------------------------------------------------------------
def test_6_9_no_forbidden_text_passes():
    assert _check(_plan(), forbidden=["dolor de espalda"]).errors == ()


def test_6_9_forbidden_substring_is_error():
    plan = _plan()
    copies = _copies(plan)
    copies[0]["primary_text"] = ["Olvida el DOLOR de espalda hoy"]
    res = _check(plan, copies=copies, forbidden=["  dolor de Espalda "])
    assert _codes(res.errors) == [FORBIDDEN_TERRITORY]
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v1",)
    assert "'dolor de Espalda'" in res.errors[0].message


# ---------------------------------------------------------------------------
# D6 — empty forbidden texts and own anchor
# ---------------------------------------------------------------------------
def test_d6_empty_forbidden_texts_ignored():
    res = _check(_plan(), forbidden=["", "   "])
    assert res.errors == () and res.warnings == ()


def test_d6_own_anchor_in_forbidden_is_warning_not_error():
    plan = _plan()
    copies = _copies(plan)
    copies[0]["headline"] = ["Envio gratis en todo"]
    res = _check(plan, copies=copies, forbidden=[OWN_ANCHOR.upper()])
    assert res.errors == ()
    assert _codes(res.warnings) == [FORBIDDEN_IS_OWN_ANCHOR]


def test_d6_own_anchor_ignored_but_other_forbidden_still_enforced():
    plan = _plan()
    copies = _copies(plan)
    copies[0]["headline"] = ["Envio gratis y sin dolor de espalda"]
    res = _check(plan, copies=copies, forbidden=[OWN_ANCHOR, "dolor de espalda"])
    assert _codes(res.errors) == [FORBIDDEN_TERRITORY]
    assert "'dolor de espalda'" in res.errors[0].message
    assert _codes(res.warnings) == [FORBIDDEN_IS_OWN_ANCHOR]


# ---------------------------------------------------------------------------
# 14.10 — new cases (P11 and rules adjusted in 14.3)
# ---------------------------------------------------------------------------
def test_6_2_anchor_case_and_spaces_normalized_is_error():
    res = check_territories(
        [_ad(0, "  Envio Gratis "), _ad(1, "envio gratis")], product_pool_size=2, buyer_pool_size=0
    )
    assert _codes(res.errors) == [ANCHOR_REPEATED]
    assert res.errors[0].ad_slots == (0, 1)
    assert repr("  Envio Gratis ") in res.errors[0].message  # text of slot i
    assert res.warnings == ()


def test_6_4_missing_or_none_plan_id_is_error():
    plan = _plan()
    copies = _copies(plan)
    del copies[0]["plan_id"]
    prompts = _prompts(plan)
    prompts[2]["plan_id"] = None
    res = _check(plan, copies=copies, prompts=prompts)
    assert _codes(res.errors) == [PLAN_ID_MISMATCH, PLAN_ID_MISMATCH]
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v1",)
    assert res.errors[1].variant_keys == (f"{PLAN_ID}_v3",)
    for issue in res.errors:
        assert "None" in issue.message and repr(PLAN_ID) in issue.message


def test_6_5_count_mismatch_too_many_items_in_both_collections():
    plan = _plan(n=2)
    copies = _copies(plan) + [_copies(plan)[0]]
    prompts = _prompts(plan) + [_prompts(plan)[1]]
    res = _check(plan, copies=copies, prompts=prompts, n=2)
    count_errors = [e for e in res.errors if e.code == COUNT_MISMATCH]
    assert len(count_errors) == 2
    assert "expected 2 copies, got 3" in count_errors[0].message
    assert "expected 2 image prompts, got 3" in count_errors[1].message
    assert count_errors[0].variant_keys == (f"{PLAN_ID}_v1",)
    assert count_errors[1].variant_keys == (f"{PLAN_ID}_v2",)


def test_6_6_empty_or_none_template_id_is_error():
    plan = _plan()
    for slot in plan["variants"]:
        slot["template_id"] = ""
    res = check_variant_slots(plan, TEMPLATES, 3)
    assert _codes(res.errors) == [TEMPLATE_NOT_IN_PROJECT] * 3
    assert "''" in res.errors[0].message

    good = _plan()
    copies = _copies(good)
    for item in copies:
        item["template_id"] = None
    res = _check(good, copies=copies)
    assert _codes(res.errors) == [TEMPLATE_NOT_IN_PROJECT] * 3
    assert [e.variant_keys for e in res.errors] == [(f"{PLAN_ID}_v{k}",) for k in (1, 2, 3)]
    assert "None" in res.errors[0].message


def test_6_7_mixed_template_in_copies_is_error():
    plan = _plan()
    copies = _copies(plan)
    copies[1]["template_id"] = TEMPLATES[2]  # valid project template, not the Ad's
    res = _check(plan, copies=copies)
    assert _codes(res.errors) == [TEMPLATE_MIXED_IN_AD]
    err = res.errors[0]
    assert err.variant_keys == (f"{PLAN_ID}_v1", f"{PLAN_ID}_v2")
    assert repr(PLAN_ID) in err.message
    assert repr(TEMPLATES[0]) in err.message and repr(TEMPLATES[2]) in err.message
    assert res.warnings == ()


def test_6_7_mixed_template_in_image_prompts_is_error():
    plan = _plan(n=6)
    prompts = _prompts(plan)
    prompts[3]["template_id"] = TEMPLATES[1]
    prompts[5]["template_id"] = TEMPLATES[2]
    res = _check(plan, prompts=prompts, n=6)
    assert _codes(res.errors) == [TEMPLATE_MIXED_IN_AD] * 2
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v1", f"{PLAN_ID}_v4")
    assert res.errors[1].variant_keys == (f"{PLAN_ID}_v1", f"{PLAN_ID}_v6")
    assert res.warnings == ()  # never a 6.10 warning, even with 6 variants > 3 templates


def test_6_7_mixed_template_in_slots_is_error_even_when_exhausted():
    plan = _plan(n=6)
    plan["variants"][4]["template_id"] = TEMPLATES[1]
    res = check_variant_slots(plan, TEMPLATES, 6)
    assert _codes(res.errors) == [TEMPLATE_MIXED_IN_AD]
    assert res.errors[0].variant_keys == (f"{PLAN_ID}_v1", f"{PLAN_ID}_v5")
    assert res.warnings == ()


def test_6_8_empty_copies_are_not_duplicates():
    plan = _plan(n=4)
    copies = _copies(plan)
    copies[0]["headline"], copies[0]["primary_text"] = "", []
    copies[1]["headline"], copies[1]["primary_text"] = "   ", None
    del copies[2]["headline"]
    del copies[2]["primary_text"]
    copies[3]["headline"], copies[3]["primary_text"] = [], [""]
    res = _check(plan, copies=copies, n=4)
    assert COPY_REPEATED not in _codes(res.errors)
    assert res.errors == ()


def test_6_8_same_headline_with_empty_text_is_not_duplicate():
    plan = _plan()
    copies = _copies(plan)
    for item in copies:
        item["headline"] = ["Igual"]
        item["primary_text"] = []
    assert _check(plan, copies=copies).errors == ()


def test_6_9_message_names_affected_field():
    plan = _plan()
    copies = _copies(plan)
    copies[0]["headline"] = ["Adios dolor"]
    copies[1]["primary_text"] = ["Sin dolor"]
    copies[2]["headline"] = ["Dolor fuera"]
    copies[2]["primary_text"] = ["Mas dolor no"]
    res = _check(plan, copies=copies, forbidden=["dolor"])
    assert _codes(res.errors) == [FORBIDDEN_TERRITORY] * 3
    m0, m1, m2 = res.error_messages()
    assert f"{PLAN_ID}_v1" in m0 and "headline contains" in m0 and "primary_text" not in m0
    assert f"{PLAN_ID}_v2" in m1 and "primary_text contains" in m1 and "headline" not in m1
    assert f"{PLAN_ID}_v3" in m2 and "headline and primary_text contain" in m2
    assert all("'dolor'" in m for m in (m0, m1, m2))


# ---------------------------------------------------------------------------
# Req 6.12 / 6.10 — Ad_Templates between Ad_Slots (check_ad_templates)
# ---------------------------------------------------------------------------
def test_6_12_distinct_ad_templates_pass():
    for n in range(1, len(TEMPLATES) + 1):
        res = check_ad_templates(slot_ad_templates(n, TEMPLATES), TEMPLATES)
        assert res.errors == () and res.warnings == ()


def test_6_12_repeated_ad_template_with_enough_templates_is_error():
    slots = ["tpl_a", "tpl_b", "tpl_a"]  # N = 3 <= 3 templates
    res = check_ad_templates(slots, TEMPLATES)
    assert _codes(res.errors) == [AD_TEMPLATE_REPEATED]
    assert res.errors[0].ad_slots == (0, 2)
    assert "'tpl_a'" in res.errors[0].message
    assert res.warnings == ()

    res = check_ad_templates(["tpl_b", "tpl_b"], TEMPLATES)  # N = 2 < 3
    assert _codes(res.errors) == [AD_TEMPLATE_REPEATED] and res.warnings == ()


def test_6_10_four_slots_three_templates_is_warning():
    slots = slot_ad_templates(4, TEMPLATES)
    assert slots == ["tpl_a", "tpl_b", "tpl_c", "tpl_a"]
    res = check_ad_templates(slots, TEMPLATES)
    assert res.ok and res.errors == ()
    assert _codes(res.warnings) == [AD_TEMPLATE_REPEATED]
    assert res.warnings[0].ad_slots == (0, 3)
    assert "exhausted" in res.warnings[0].message


def test_6_12_check_ad_templates_does_not_mutate_and_is_deterministic():
    slots = ["tpl_a", "tpl_a", "tpl_c"]
    before = list(slots)
    assert check_ad_templates(slots, TEMPLATES) == check_ad_templates(slots, TEMPLATES)
    assert slots == before


def test_checker_is_deterministic():
    plan = _plan()
    copies = _copies(plan)
    copies[0]["plan_id"] = "x"
    assert _check(plan, copies=copies) == _check(plan, copies=copies)
    ads = [_ad(0, "a"), _ad(1, "a")]
    assert check_territories(ads, product_pool_size=2, buyer_pool_size=0) == check_territories(
        ads, product_pool_size=2, buyer_pool_size=0
    )


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all diversity-checker unit tests passed")
