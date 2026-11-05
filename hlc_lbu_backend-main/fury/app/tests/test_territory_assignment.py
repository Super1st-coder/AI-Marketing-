"""Invariant tests for the deterministic territory-assignment engine (Ads Assembly v2 §4).

Runnable two ways:
    python -m tests.test_territory_assignment      # plain asserts, prints a summary
    pytest tests/test_territory_assignment.py      # standard collection
"""
from __future__ import annotations

import copy

from agents.tools.mock_sinergia import _MOCK_ADSET
from schemas.territory_schemas import PRODUCT_ANCHOR_CATEGORIES, BUYER_ANCHOR_CATEGORIES
from services.territory_assignment import (
    assign_territories,
    inventory_anchors,
    unwrap_adset,
    build_estratega_adset_input,
    apply_descriptions,
    territory_to_plan,
    AXIS_VOCAB,
)

_LEGACY_PLAN_KEYS = {
    "id", "concept", "emocion", "intencion", "visual_dominante", "contexto_uso",
    "psicologia", "tone", "color_palette", "target_insight", "template_id",
    "template_selection_reason",
}


def _ctx():
    return copy.deepcopy(_MOCK_ADSET)


def _pools():
    adset = unwrap_adset(_ctx())
    return inventory_anchors(adset, "product"), inventory_anchors(adset, "buyer")


def test_unwrap_handles_both_shapes():
    inner = unwrap_adset(_ctx())
    assert inner.get("id") == 173 and "campaign" in inner
    # real (single-wrapped) shape
    real = {"ok": True, "adset": {"id": 999, "campaign": {}}}
    assert unwrap_adset(real).get("id") == 999


def test_umbrella_refs_populated():
    ads = assign_territories(_ctx(), n_ads=4)
    assert ads, "expected territories"
    # umbrella_reference <- umbrella.summary.big_idea ; concept_reference <- umbrella.title
    assert all(a.umbrella_reference and "Para Todos tus Mundos" in a.umbrella_reference for a in ads)
    assert all(a.campaign_concept_reference == "Para Todos tus Mundos" for a in ads)


def test_primary_anchors_distinct_within_pool():
    product_pool, buyer_pool = _pools()
    n = min(len(product_pool), len(buyer_pool)) * 2  # keeps each side within its pool
    assert n >= 2, f"mock too sparse (product={len(product_pool)} buyer={len(buyer_pool)})"
    ads = assign_territories(_ctx(), n_ads=n)

    prod = [a.territory.anchor_primary.text for i, a in enumerate(ads) if i % 2 == 0]
    buy = [a.territory.anchor_primary.text for i, a in enumerate(ads) if i % 2 == 1]
    assert len(prod) == len(set(prod)), f"product primaries not distinct: {prod}"
    assert len(buy) == len(set(buy)), f"buyer primaries not distinct: {buy}"


def test_parity_rotation():
    ads = assign_territories(_ctx(), n_ads=4)
    for i, a in enumerate(ads):
        cat = a.territory.anchor_primary.category
        if i % 2 == 0:
            assert cat in PRODUCT_ANCHOR_CATEGORIES, f"slot {i} expected product anchor, got {cat}"
        else:
            assert cat in BUYER_ANCHOR_CATEGORIES, f"slot {i} expected buyer anchor, got {cat}"


def test_style_axes_disjoint_until_exhausted():
    n = 5
    ads = assign_territories(_ctx(), n_ads=n)
    for axis, vocab in AXIS_VOCAB.items():
        vals = [getattr(a.territory.axes, axis) for a in ads]
        k = min(n, len(vocab))
        assert len(set(vals[:k])) == k, f"axis {axis} not disjoint in first {k}: {vals}"


def test_territorio_prohibido_is_all_other_primaries():
    ads = assign_territories(_ctx(), n_ads=4)
    primaries = [a.territory.anchor_primary.text for a in ads]
    for i, a in enumerate(ads):
        expected = {t for j, t in enumerate(primaries) if j != i}
        assert set(a.territorio_prohibido) == expected
        assert a.territory.anchor_primary.text not in a.territorio_prohibido


def test_empty_context_returns_empty():
    assert assign_territories({"ok": True, "adset": {"data": {"campaign": {}, "buyer": {}}}}, n_ads=3) == []


def test_build_estratega_adset_input_carries_umbrella_and_territories():
    ads = assign_territories(_ctx(), n_ads=4)
    msg = build_estratega_adset_input(_ctx(), ads)
    assert "Para Todos tus Mundos" in msg          # umbrella big_idea + title
    assert "core_message" in msg                    # normalized thread carries summary fields
    assert "hero" in msg                            # summary hero_story surfaced
    assert "territorio_prohibido" in msg
    assert '"index"' in msg


def test_apply_descriptions_merges_by_index_only_concept():
    ads = assign_territories(_ctx(), n_ads=3)
    before = [a.territory.anchor_primary.text for a in ads]  # must be untouched
    llm = [
        {"index": 2, "concept": "  C2  "},
        {"index": 0, "concept": "C0"},
        # index 1 intentionally omitted
    ]
    out = apply_descriptions(ads, llm)
    assert out[0].concept == "C0"
    assert out[2].concept == "C2"           # trimmed + matched by index, not position
    assert out[1].concept is None            # missing item left as-is
    assert [a.territory.anchor_primary.text for a in out] == before  # territory not mutated


def test_territory_to_plan_is_legacy_compatible():
    ads = assign_territories(_ctx(), n_ads=3, template_ids=["tplA", "tplB"])
    ads = apply_descriptions(ads, [{"index": i, "concept": f"c{i}"} for i in range(3)])
    plans = [territory_to_plan(a, i) for i, a in enumerate(ads)]
    assert _LEGACY_PLAN_KEYS <= set(plans[0])          # downstream steps see the shape they expect
    assert plans[0]["template_id"] == "tplA" and plans[1]["template_id"] == "tplB"
    assert plans[0]["emocion"] == ads[0].territory.axes.emocion   # axes carried through 1:1
    assert plans[0]["target_insight"] == ads[0].territory.anchor_primary.text


if __name__ == "__main__":
    product_pool, buyer_pool = _pools()
    print(f"anchor pools: product={len(product_pool)} buyer={len(buyer_pool)}")
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn()
        print(f"  PASS  {fn.__name__}")
    ads = assign_territories(_ctx(), n_ads=6)
    print(f"\nassigned {len(ads)} territories:")
    for i, a in enumerate(ads):
        t = a.territory
        print(f"  slot {i}: [{t.anchor_primary.category}] {t.anchor_primary.text[:44]!r} "
              f"| emocion={t.axes.emocion} visual={t.axes.visual_dominante} palette={t.palette_family}")
    print("\nALL INVARIANTS PASS")
