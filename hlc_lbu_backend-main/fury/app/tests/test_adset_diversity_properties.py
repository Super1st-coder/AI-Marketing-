"""Property-based tests for services/adset_diversity.py (adset-creative-diversity).
Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_properties.py
    PYTHONPATH=. python -m tests.test_adset_diversity_properties
"""
from contextlib import contextmanager

from hypothesis import given, settings
from hypothesis import strategies as st
from loguru import logger

from services.adset_diversity import (
    assign_variant_angles,
    bind_territories,
    build_creative_plan,
    build_variant_slots,
    extract_adset_ads,
    resolve_ad_slots,
    resolve_project_templates,
    template_order,
)
from schemas.territory_schemas import BUYER_ANCHOR_CATEGORIES, PRODUCT_ANCHOR_CATEGORIES
from services.territory_assignment import (
    AXIS_VOCAB,
    PALETTE_FAMILIES,
    assign_territories,
    unwrap_adset,
)
from tests._diversity_pipeline_fakes import make_adset_context

# ---------------------------------------------------------------------------
# Generators (reusable by the other properties of this file)
# ---------------------------------------------------------------------------

# Small positive range so valid ids repeat often.
valid_ad_ids = st.integers(min_value=1, max_value=30)
invalid_ad_ids = st.one_of(
    st.just(0),
    st.integers(min_value=-30, max_value=-1),
    st.booleans(),
    st.sampled_from(["1", "7", "abc", ""]),
    st.none(),
)
# An Ad entry: a raw id (wrapped by `make_ad`) or a dict without `id`.
ad_entries = st.one_of(
    valid_ad_ids,
    valid_ad_ids,  # weight valid ids higher
    invalid_ad_ids,
    st.just({"name": "Ad without id"}),
)
ad_entry_lists = st.lists(ad_entries, max_size=12)
adset_forms = st.sampled_from(["mock", "real"])


def build_adset_context(entries, form: str) -> dict:
    """Adset_Context with `entries` as its Ads, in mock (`adset.data`) or real (`adset`) form."""
    ctx = make_adset_context(entries)
    if form == "real":
        return {"ok": True, "adset": unwrap_adset(ctx)}
    return ctx


def is_valid_ad_id(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def entry_id(entry):
    return entry.get("id") if isinstance(entry, dict) else entry


@st.composite
def id_ad_choices(draw, valid_ids: list[int]):
    """`id_ad` ∈ {None, 0, an id present in the Adset_Ads, an absent id}."""
    kinds = ["none", "zero", "absent"] + (["present"] if valid_ids else [])
    kind = draw(st.sampled_from(kinds))
    if kind == "none":
        return None
    if kind == "zero":
        return 0
    if kind == "present":
        return draw(st.sampled_from(valid_ids))
    return draw(st.integers(min_value=1, max_value=60).filter(lambda i: i not in valid_ids))


@contextmanager
def capture_warnings(task_id: str):
    """Collect loguru WARNING messages tagged with `[{task_id}]`."""
    messages: list[str] = []
    tag = f"[{task_id}]"

    def sink(message):
        record = message.record
        if record["level"].name == "WARNING" and tag in record["message"]:
            messages.append(record["message"])

    handler_id = logger.add(sink, level="WARNING")
    try:
        yield messages
    finally:
        logger.remove(handler_id)


# ---------------------------------------------------------------------------
# Property 3
# ---------------------------------------------------------------------------


# Feature: adset-creative-diversity, Property 3: Resolución de Ad_Slots determinista
@settings(max_examples=100, deadline=None)
@given(data=st.data(), entries=ad_entry_lists, form=adset_forms)
def test_ad_slot_resolution_is_deterministic(data, entries, form):
    """**Validates: Requirements 3.1, 3.2, 3.5, 3.6, 3.7**"""
    task_id = "task-p3"
    raw_ids = [entry_id(e) for e in entries]
    expected_ids = sorted({i for i in raw_ids if is_valid_ad_id(i)})

    # Req 3.1, 3.2: valid ids, deduplicated, ascending; one warning per discarded entry.
    with capture_warnings(task_id) as warnings:
        ad_ids = extract_adset_ads(build_adset_context(entries, form), task_id)
    assert ad_ids == expected_ids
    assert len(warnings) == len(entries) - len(expected_ids)

    # Independent of the input order and of the mock/real form.
    shuffled = data.draw(st.permutations(entries), label="shuffled")
    other_form = data.draw(adset_forms, label="other_form")
    assert extract_adset_ads(build_adset_context(shuffled, other_form), task_id) == ad_ids

    id_ad = data.draw(id_ad_choices(ad_ids), label="id_ad")
    with capture_warnings(task_id) as warnings:
        plan = resolve_ad_slots(ad_ids, id_ad, task_id)

    if not id_ad:
        # Req 3.7: Scenario_1 processes every Adset_Ad.
        assert plan.slot_ad_ids == ad_ids
        assert plan.target_ad_ids == ad_ids
        assert plan.extra_slot is False
        assert warnings == []
    elif id_ad in ad_ids:
        # Req 3.5: Scenario_2 with a known Ad keeps the slots, targets only id_ad.
        assert plan.slot_ad_ids == ad_ids
        assert plan.target_ad_ids == [id_ad]
        assert plan.extra_slot is False
        assert warnings == []
    else:
        # Req 3.6: unknown id_ad gets the extra slot len(Adset_Ads), with a warning.
        assert plan.slot_ad_ids == ad_ids + [id_ad]
        assert plan.slot_ad_ids.index(id_ad) == len(ad_ids)
        assert plan.target_ad_ids == [id_ad]
        assert plan.extra_slot is True
        assert len(warnings) == 1 and str(id_ad) in warnings[0]
    assert ad_ids == expected_ids  # input list not mutated

    # Req 3.2: each Ad_Slot's territory is bound to its Ad's id (deep copy, territory intact).
    if plan.slot_ad_ids:
        ctx = build_adset_context(entries, form)
        territories = assign_territories(ctx, n_ads=len(plan.slot_ad_ids), adset_id=7, n_variantes=1)
        if territories:
            before = [t.model_dump() for t in territories]
            bound = bind_territories(territories, plan.slot_ad_ids)
            assert [t.ad_id for t in bound] == plan.slot_ad_ids
            for original, b in zip(territories, bound):
                assert b is not original
                assert b.territory == original.territory
                assert b.territorio_prohibido == original.territorio_prohibido
            assert [t.model_dump() for t in territories] == before
            try:
                bind_territories(territories, plan.slot_ad_ids + [999])
            except ValueError:
                pass
            else:
                raise AssertionError("bind_territories must reject a slot/territory length mismatch")


# ---------------------------------------------------------------------------
# Property 4
# ---------------------------------------------------------------------------

_BUYER_PAYLOAD_KEYS = {
    "barriers_to_change": "barriers_to_making_a_change",
    "customer_location": "hometown",
}


@st.composite
def anchor_pools(draw):
    """(product_details, buyer_attributes) with per-category lists of arbitrary size,
    at least one anchor in total. Texts are unique so slots are distinguishable."""
    def side(categories, prefix):
        pool = {}
        for cat in categories:
            n = draw(st.integers(min_value=0, max_value=3), label=f"{prefix}.{cat}")
            if n:
                key = _BUYER_PAYLOAD_KEYS.get(cat, cat) if prefix == "buyer" else cat
                pool[key] = [f"{prefix}-{cat}-{i}" for i in range(n)]
        return pool

    product = side(PRODUCT_ANCHOR_CATEGORIES, "product")
    buyer = side(BUYER_ANCHOR_CATEGORIES, "buyer")
    if not product and not buyer:
        cat = draw(st.sampled_from(PRODUCT_ANCHOR_CATEGORIES + BUYER_ANCHOR_CATEGORIES))
        if cat in PRODUCT_ANCHOR_CATEGORIES:
            product[cat] = [f"product-{cat}-0"]
        else:
            buyer[_BUYER_PAYLOAD_KEYS.get(cat, cat)] = [f"buyer-{cat}-0"]
    return product, buyer


def build_adset_context_with_pools(entries, form: str, pools) -> dict:
    """`build_adset_context` with the anchor pools replaced by `pools`."""
    product, buyer = pools
    ctx = build_adset_context(entries, form)
    adset = unwrap_adset(ctx)
    adset["campaign"]["product_details"] = dict(product)
    adset["campaign"]["bperson_details"] = {}
    adset.setdefault("buyer", {})["attributes"] = dict(buyer)
    return ctx


def territories_by_ad_id(ctx, task_id: str, id_ad=None) -> dict:
    """Diversity_Path slot resolution + assignment + binding, keyed by `ad_id`."""
    plan = resolve_ad_slots(extract_adset_ads(ctx, task_id), id_ad, task_id)
    territories = assign_territories(ctx, n_ads=len(plan.slot_ad_ids), adset_id=7, n_variantes=1)
    return {t.ad_id: t for t in bind_territories(territories, plan.slot_ad_ids)}


# Feature: adset-creative-diversity, Property 4: Territorio estable por slot
@settings(max_examples=100, deadline=None)
@given(
    data=st.data(),
    pools=anchor_pools(),
    entries=st.lists(valid_ad_ids, min_size=1, max_size=10, unique=True),
    form=adset_forms,
)
def test_territory_is_stable_per_slot(data, pools, entries, form):
    """**Validates: Requirements 3.4, 3.5, 12.4, 12.6**"""
    task_id = "task-p4"
    ctx = build_adset_context_with_pools(entries, form, pools)

    # Req 3.4: the territory of slot i does not depend on n_ads.
    n2 = data.draw(st.integers(min_value=1, max_value=16), label="n2")
    n1 = data.draw(st.integers(min_value=1, max_value=n2), label="n1")
    short = assign_territories(ctx, n_ads=n1, n_variantes=1)
    long = assign_territories(ctx, n_ads=n2, n_variantes=1)
    assert len(short) == n1 and len(long) == n2
    assert [t.territory for t in short] == [t.territory for t in long[:n1]]

    # Req 12.6: Ads in a different order (and other payload form) -> same territories per ad_id.
    shuffled = data.draw(st.permutations(entries), label="shuffled")
    other_form = data.draw(adset_forms, label="other_form")
    with capture_warnings(task_id):
        scenario_1 = territories_by_ad_id(ctx, task_id)
        reordered = territories_by_ad_id(
            build_adset_context_with_pools(shuffled, other_form, pools), task_id
        )
    assert set(scenario_1) == set(entries)
    assert {k: v.territory for k, v in reordered.items()} == {
        k: v.territory for k, v in scenario_1.items()
    }
    assert {k: v.territorio_prohibido for k, v in reordered.items()} == {
        k: v.territorio_prohibido for k, v in scenario_1.items()
    }

    # Req 3.5, 12.4: Scenario_2 with a known id_ad keeps its Scenario_1 slot territory.
    id_ad = data.draw(st.sampled_from(entries), label="id_ad")
    with capture_warnings(task_id):
        scenario_2 = territories_by_ad_id(ctx, task_id, id_ad=id_ad)
    assert scenario_2[id_ad].territory == scenario_1[id_ad].territory
    assert scenario_2[id_ad].territorio_prohibido == scenario_1[id_ad].territorio_prohibido


# ---------------------------------------------------------------------------
# Property 5
# ---------------------------------------------------------------------------


def expected_sides(n_ads: int, product_size: int, buyer_size: int) -> list[str]:
    """Req 3.8 side rule: even slot -> product, odd -> buyer; all to the non-empty
    side if the other pool is empty."""
    sides = []
    for slot in range(n_ads):
        side = "product" if slot % 2 == 0 else "buyer"
        if side == "product" and not product_size:
            side = "buyer"
        elif side == "buyer" and not buyer_size:
            side = "product"
        sides.append(side)
    return sides


# Feature: adset-creative-diversity, Property 5: Disyunción de anclas y ejes dentro de los límites
@settings(max_examples=100, deadline=None)
@given(
    pools=anchor_pools(),
    entries=st.lists(valid_ad_ids, min_size=1, max_size=10, unique=True),
    form=adset_forms,
    n_ads=st.integers(min_value=1, max_value=16),
)
def test_anchor_and_axis_disjointness_within_limits(pools, entries, form, n_ads):
    """**Validates: Requirements 3.8, 3.9**"""
    product, buyer = pools
    pool_size = {
        "product": sum(len(v) for v in product.values()),
        "buyer": sum(len(v) for v in buyer.values()),
    }
    ctx = build_adset_context_with_pools(entries, form, pools)
    territories = assign_territories(ctx, n_ads=n_ads, adset_id=7, n_variantes=1)
    assert len(territories) == n_ads

    sides = expected_sides(n_ads, pool_size["product"], pool_size["buyer"])
    per_side = {s: sides.count(s) for s in ("product", "buyer")}

    for i in range(n_ads):
        ti = territories[i].territory
        for j in range(i + 1, n_ads):
            tj = territories[j].territory
            # Req 3.8: distinct anchor_primary while each slot's side is within its pool.
            if per_side[sides[i]] <= pool_size[sides[i]] and per_side[sides[j]] <= pool_size[sides[j]]:
                assert ti.anchor_primary.text != tj.anchor_primary.text, (i, j, sides)
            # Req 3.9: distinct value per axis while n_ads fits the vocabulary.
            for axis, vocab in AXIS_VOCAB.items():
                if n_ads <= len(vocab):
                    assert getattr(ti.axes, axis) != getattr(tj.axes, axis), (axis, i, j)
            if n_ads <= len(PALETTE_FAMILIES):
                assert ti.palette_family != tj.palette_family, (i, j)


# ---------------------------------------------------------------------------
# Property 6
# ---------------------------------------------------------------------------


def assert_forbidden_are_other_anchors(territories) -> None:
    """Req 3.10: slot i forbids exactly the other slots' anchor texts, in slot order;
    its own text only appears if another slot repeats it (pool exhaustion)."""
    primaries = [t.territory.anchor_primary.text for t in territories]
    for i, t in enumerate(territories):
        others = [text for j, text in enumerate(primaries) if j != i]
        assert t.territorio_prohibido == others, (i, primaries)
        own_in_forbidden = primaries[i] in t.territorio_prohibido
        assert own_in_forbidden == (primaries.count(primaries[i]) > 1), (i, primaries)


# Feature: adset-creative-diversity, Property 6: Forbidden_Territories son los anclas de los demás slots
@settings(max_examples=100, deadline=None)
@given(
    data=st.data(),
    pools=anchor_pools(),
    entries=st.lists(valid_ad_ids, min_size=1, max_size=10, unique=True),
    form=adset_forms,
    n_ads=st.integers(min_value=1, max_value=16),
)
def test_forbidden_territories_are_other_slots_anchors(data, pools, entries, form, n_ads):
    """**Validates: Requirements 3.5, 3.10**"""
    task_id = "task-p6"
    ctx = build_adset_context_with_pools(entries, form, pools)

    # Req 3.10: for any n_ads, directly on the Territory_Engine output.
    territories = assign_territories(ctx, n_ads=n_ads, adset_id=7, n_variantes=1)
    assert len(territories) == n_ads
    assert_forbidden_are_other_anchors(territories)

    # Req 3.5, 3.10: Diversity_Path slots (Scenario_1 / Scenario_2, incl. the extra slot).
    ad_ids = sorted(entries)
    id_ad = data.draw(id_ad_choices(ad_ids), label="id_ad")
    with capture_warnings(task_id):
        plan = resolve_ad_slots(extract_adset_ads(ctx, task_id), id_ad, task_id)
    slot_territories = assign_territories(
        ctx, n_ads=len(plan.slot_ad_ids), adset_id=7, n_variantes=1
    )
    bound = bind_territories(slot_territories, plan.slot_ad_ids)
    assert_forbidden_are_other_anchors(bound)

    # The target Ad's forbidden list covers every sibling slot (extra slot included).
    by_ad = {t.ad_id: t for t in bound}
    for target in plan.target_ad_ids:
        siblings = [t.territory.anchor_primary.text for t in bound if t.ad_id != target]
        assert by_ad[target].territorio_prohibido == siblings


# ---------------------------------------------------------------------------
# Property 7
# ---------------------------------------------------------------------------

template_ids = st.one_of(
    st.integers(min_value=1, max_value=10_000),
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=12),
)


# Small pool so identifiers repeat, including int/str collisions (7 vs "7").
_pooled_template_ids = st.one_of(
    st.sampled_from([7, "7", "a", "b", 42, "42"]),
    template_ids,
)
_empty_ids = st.sampled_from([None, ""])


def _expected_template_id(entry):
    """Oracle: `id` unless missing/empty, then `template_id`; None if neither."""
    if not isinstance(entry, dict):
        return None
    for key in ("id", "template_id"):
        value = entry.get(key)
        if value is not None and value != "":
            return value
    return None


@st.composite
def _template_entry(draw):
    kind = draw(st.sampled_from(
        ["id", "template_id", "empty_id_fallback", "both", "unresolvable", "non_dict"]))
    name = {"name": draw(st.text(max_size=4))}
    if kind == "id":
        return {"id": draw(_pooled_template_ids), **name}
    if kind == "template_id":
        return {"template_id": draw(_pooled_template_ids), **name}
    if kind == "empty_id_fallback":
        entry = {"template_id": draw(_pooled_template_ids), **name}
        if draw(st.booleans()):
            entry["id"] = draw(_empty_ids)
        return entry
    if kind == "both":  # `id` wins over `template_id`
        return {"id": draw(_pooled_template_ids),
                "template_id": draw(_pooled_template_ids), **name}
    if kind == "unresolvable":
        return draw(st.sampled_from([
            {}, dict(name), {"id": None}, {"id": ""}, {"template_id": ""},
            {"id": "", "template_id": None}, {"id": None, "template_id": ""},
        ]))
    return draw(st.one_of(st.none(), st.integers(), st.text(max_size=4),
                          st.lists(st.integers(), max_size=2)))


@st.composite
def template_contexts(draw):
    """`get_template_context` result mixing repeated ids, entries without `id`/`template_id`,
    empty values, ints and non-dicts. Oracle: first occurrence as `str`, in order."""
    templates = draw(st.lists(_template_entry(), max_size=10))
    expected: list[str] = []
    for entry in templates:
        value = _expected_template_id(entry)
        if value is not None and str(value) not in expected:
            expected.append(str(value))
    return {"ok": True, "templates": templates}, expected


# Feature: adset-creative-diversity, Property 7: Una plantilla por Ad y resolución de Project_Templates
@settings(max_examples=100, deadline=None)
@given(
    data=st.data(),
    context_and_ids=template_contexts(),
    plan_id=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=1, max_size=16),
    ad_slot=st.integers(min_value=0, max_value=50),
    # Covers n_variants > 4 and > len(templates): no upper bound (P7, Req 4.9).
    n_variants=st.integers(min_value=1, max_value=20),
    seed=st.text(max_size=12),
)
def test_template_rotation_per_variant_slot(data, context_and_ids, plan_id, ad_slot,
                                            n_variants, seed):
    """**Validates: Requirements 4.5, 4.6, 4.9, 14.1**"""
    context, expected_ids = context_and_ids
    templates = resolve_project_templates(context)
    assert templates == expected_ids

    if not templates:  # no resolvable id → empty Project_Templates → ValueError
        try:
            build_variant_slots(plan_id, ad_slot, n_variants, templates)
        except ValueError:
            return
        raise AssertionError("build_variant_slots must raise ValueError on empty templates")

    # The ordered list passed to build_variant_slots is any permutation of the resolved
    # Project_Templates (identity and the job's Template_Order included, D15).
    candidate_orders = [
        list(templates),
        template_order(templates, seed),
        data.draw(st.permutations(templates), label="order"),
    ]
    # P14 (Req 14.1): slot k carries angles[k - 1], independent of ad_slot and order.
    expected_angles = assign_variant_angles(plan_id, n_variants)
    other_ad_slot = data.draw(st.integers(min_value=0, max_value=50), label="other_ad_slot")
    for order in candidate_orders:
        assert sorted(order) == sorted(templates)
        slots = build_variant_slots(plan_id, ad_slot, n_variants, order)
        assert len(slots) == n_variants
        for k, slot in enumerate(slots, start=1):
            assert slot["variant_key"] == f"{plan_id}_v{k}"
            # P11/P12: every Variant_Slot of the Ad shares the single Ad_Template.
            assert slot["template_id"] == order[ad_slot % len(order)]
            assert slot["angle"] == expected_angles[k - 1]
        assert len({s["variant_key"] for s in slots}) == n_variants
        other_slots = build_variant_slots(plan_id, other_ad_slot, n_variants, order)
        assert [s["angle"] for s in other_slots] == expected_angles

    # Empty Project_Templates (explicit, or resolved from an `ok: False` context) → ValueError.
    failed_ctx = {"ok": False, "templates": context["templates"]}
    for empty in ([], resolve_project_templates(failed_ctx)):
        try:
            build_variant_slots(plan_id, ad_slot, n_variants, empty)
        except ValueError:
            pass
        else:
            raise AssertionError("build_variant_slots must raise ValueError on empty templates")


# ---------------------------------------------------------------------------
# Property 8
# ---------------------------------------------------------------------------

AXIS_NAMES = ("emocion", "intencion", "visual_dominante", "contexto_uso", "psicologia")
concepts = st.text(min_size=1, max_size=40).filter(lambda s: s.strip())


@st.composite
def ad_descriptions(draw):
    """(AdDescription, ad_slot) from the Territory_Engine over generated anchor pools,
    bound to a positive `ad_id`, with a non-empty `concept` and an arbitrary legacy
    `template_id` (which the Creative_Plan must drop)."""
    pools = draw(anchor_pools(), label="pools")
    n_ads = draw(st.integers(min_value=1, max_value=12), label="n_ads")
    ad_slot = draw(st.integers(min_value=0, max_value=n_ads - 1), label="ad_slot")
    ctx = build_adset_context_with_pools([1], "mock", pools)
    territory = assign_territories(ctx, n_ads=n_ads, adset_id=7, n_variantes=1)[ad_slot]
    ad = territory.model_copy(
        deep=True,
        update={
            "ad_id": draw(st.integers(min_value=1, max_value=10_000), label="ad_id"),
            "concept": draw(concepts, label="concept"),
            "template_id": draw(st.one_of(st.none(), st.sampled_from(["tpl-a", "42"])),
                                label="template_id"),
        },
    )
    return ad, ad_slot


# Feature: adset-creative-diversity, Property 8: El Creative_Plan conserva el territorio
@settings(max_examples=100, deadline=None)
@given(
    ad_and_slot=ad_descriptions(),
    templates=st.lists(st.sampled_from(["t1", "t2", "t3", "t4", "t5"]), min_size=1, max_size=5),
    n_variants=st.integers(min_value=1, max_value=8),
)
def test_creative_plan_preserves_territory(ad_and_slot, templates, n_variants):
    """**Validates: Requirements 4.1, 4.3, 14.4**"""
    ad, ad_slot = ad_and_slot
    before = ad.model_dump()
    plan_id = f"plan_ad_{ad.ad_id}"
    slots = build_variant_slots(plan_id, ad_slot, n_variants, templates)

    plan = build_creative_plan(ad, ad.ad_id, ad_slot, slots)
    t = ad.territory

    # Req 4.1: one plan per Ad, id plan_ad_{ad_id}, variants == slots, no legacy template keys.
    assert plan["id"] == plan_id
    assert plan["variants"] == slots
    # P14 (Req 14.1): each slot keeps its Variant_Angle (slot k → angles[k - 1]).
    assert [v["angle"] for v in plan["variants"]] == assign_variant_angles(plan_id, n_variants)
    assert "template_id" not in plan
    assert "template_selection_reason" not in plan
    assert plan["concept"] == ad.concept

    # Req 4.3: Territory_Engine values preserved verbatim.
    assert plan["target_insight"] == t.anchor_primary.text
    assert plan["_territory"]["anchor_primary"] == t.anchor_primary.model_dump()
    for axis in AXIS_NAMES:
        assert plan[axis] == getattr(t.axes, axis), axis
    assert plan["color_palette"] == t.palette_family
    assert plan["_territory"]["palette_family"] == t.palette_family
    assert plan["_territory"]["derivados"] == t.derivados.model_dump()
    assert plan["_territory"]["territorio_prohibido"] == ad.territorio_prohibido

    # Req 14.4: the Variant_Angle assignment changes nothing else in the plan. The plan
    # built from the same slots without `angle` equals this one once `angle` is dropped
    # from each element of `variants`.
    slots_without_angle = [{k: v for k, v in s.items() if k != "angle"} for s in slots]
    plan_without_angle = build_creative_plan(ad, ad.ad_id, ad_slot, slots_without_angle)
    stripped = {
        **plan,
        "variants": [{k: v for k, v in s.items() if k != "angle"} for s in plan["variants"]],
    }
    assert stripped == plan_without_angle
    # Building the plans does not mutate the input slots.
    assert [s["angle"] for s in slots] == assign_variant_angles(plan_id, n_variants)

    # The input AdDescription is not mutated.
    assert ad.model_dump() == before


# ---------------------------------------------------------------------------
# Property 9: Validación de forma por Variant_Slot
# ---------------------------------------------------------------------------

P9_TASK_ID = "task-p9"
P9_ID_ADSET = 7
P9_AD_ID = 101
P9_PLAN_ID = f"plan_ad_{P9_AD_ID}"

P9_MUTATIONS = (
    "delete", "duplicate", "reorder", "change_plan_id", "change_variant_key",
    "drop_variant_key", "change_template_id", "empty",
)


def p9_copy_item(slot: dict) -> dict:
    return {
        "plan_id": P9_PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "headline": [f"H {slot['variant_key']}"],
        "primary_text": ["P"],
        "description": ["D"],
        "cta": ["LEARN_MORE"],
        "template_elements": [{"element_id": "title", "text": "H"}],
    }


def p9_prompt_item(slot: dict) -> dict:
    return {
        "plan_id": P9_PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "image_prompts": [{"element_id": "img", "image_prompt": "x", "image_request": "y"}],
    }


@st.composite
def p9_slots(draw):
    templates = draw(st.lists(st.sampled_from(["tA", "tB", "tC", "tD"]),
                              min_size=1, max_size=3, unique=True))
    n_variants = draw(st.integers(min_value=1, max_value=4))
    ad_slot = draw(st.integers(min_value=0, max_value=5))
    return build_variant_slots(P9_PLAN_ID, ad_slot=ad_slot, n_variants=n_variants,
                               project_templates=templates)


@st.composite
def p9_mutated_items(draw, valid_items: list[dict], slots: list[dict]):
    """A valid response with zero or more mutations applied in sequence."""
    import copy as _copy

    items = _copy.deepcopy(valid_items)
    keys = [s["variant_key"] for s in slots]
    for op in draw(st.lists(st.sampled_from(P9_MUTATIONS), max_size=4)):
        if op == "empty":
            items = []
            continue
        if not items:
            continue
        i = draw(st.integers(min_value=0, max_value=len(items) - 1))
        if op == "delete":
            items.pop(i)
        elif op == "duplicate":
            items.insert(i, _copy.deepcopy(items[i]))
        elif op == "reorder":
            items = draw(st.permutations(items))
        elif op == "change_plan_id":
            items[i]["plan_id"] = draw(st.sampled_from(["plan_ad_999", "plan_1", P9_PLAN_ID + "x"]))
        elif op == "change_variant_key":
            items[i]["variant_key"] = draw(st.sampled_from(keys + [f"{P9_PLAN_ID}_v99", "other_v1"]))
        elif op == "drop_variant_key":
            items[i].pop("variant_key", None)
        elif op == "change_template_id":
            items[i]["template_id"] = draw(st.sampled_from(["tA", "tB", "tC", "tD", "tZ"]))
    return items


@st.composite
def p9_with_angles(draw, items: list[dict], slots: list[dict]):
    """Per item: no `angle`, an arbitrary `angle`, or its slot's angle (Req 14.7)."""
    import copy as _copy

    items = _copy.deepcopy(items)
    angles = [s["angle"] for s in slots]
    for it in items:
        mode = draw(st.sampled_from(["none", "arbitrary", "slot"]))
        if mode == "none":
            it.pop("angle", None)
        elif mode == "arbitrary":
            it["angle"] = draw(st.one_of(
                st.sampled_from(angles),  # another slot's angle
                st.dictionaries(st.sampled_from(["hook", "headline_structure", "copy_length"]),
                                st.text(max_size=12), max_size=3),
                st.text(max_size=12), st.none(), st.integers(),
            ))
        else:
            match = [s for s in slots if s["variant_key"] == it.get("variant_key")]
            it["angle"] = match[0]["angle"] if match else draw(st.sampled_from(angles))
    return items


def p9_expected_valid(items: list[dict], slots: list[dict]) -> bool:
    """Oracle: exactly one item per slot with matching (plan_id, variant_key, template_id)."""
    got = sorted(
        (str(it.get("plan_id")), str(it.get("variant_key")), str(it.get("template_id")))
        for it in items
    )
    want = sorted((P9_PLAN_ID, s["variant_key"], s["template_id"]) for s in slots)
    return bool(items) and got == want


def jrs_attempts() -> int:
    import services.job_runner_service as jrs

    return jrs._DIVERSITY_AGENT_ATTEMPTS


@contextmanager
def p9_pipeline(responses: dict, slots=()):
    """Patches job_runner_service `_run_agent` / `_redis` with fakes (restored on exit)."""
    import json

    import services.job_runner_service as jrs
    from tests._diversity_pipeline_fakes import (
        COPYWRITER,
        IMAGE_PROMPTER,
        FakeAgentFactories,
        FakeGetATemplateDefinition,
        FakeRedis,
        FakeRunAgent,
    )
    from services.adset_diversity import DEFAULT_DECORATIVE_IMAGE_PATTERNS

    run_agent = FakeRunAgent(responses)
    redis = FakeRedis()
    saved = (jrs._run_agent, jrs._redis)
    jrs._run_agent = run_agent
    jrs._redis = lambda: redis

    async def _validate_ctas(copies):
        return None

    factories = FakeAgentFactories()
    deps = jrs._DiversityDeps(
        get_template_context=None, delete_variants=None, validate_ctas=_validate_ctas,
        save_ads_programmatically=None, generate_images=None, build_abyssale_payload=None,
        post_to_abyssale_and_wait=None, make_estratega_adset_agent=None,
        make_copywriter_agent=factories[COPYWRITER],
        make_image_prompter_agent=factories[IMAGE_PROMPTER],
        make_validador_adset_agent=None, progress=lambda *_: None,
        template_definitions=jrs._JobTemplateDefinitions(
            FakeGetATemplateDefinition(), DEFAULT_DECORATIVE_IMAGE_PATTERNS),
    )
    ctx = make_adset_context([P9_AD_ID])
    ids = tuple(dict.fromkeys(s["template_id"] for s in slots))  # the case's template_ids
    job = jrs._DiversityJob(
        task=None, task_id=P9_TASK_ID, id_adset=P9_ID_ADSET, n_variants=1,
        project_id="test-project-id", id_ad=None, custom_prompt=None,
        add_variant=True, id_variant=None, adset_context=ctx,
        adset_context_json=json.dumps(ctx),
    )
    ad = jrs._DiversityAdInput(
        ad_id=P9_AD_ID, ad_slot=0, territory=None, all_territories=(), forbidden=(),
        templates=jrs._JobTemplates(ids, ids),
    )
    try:
        yield jrs, deps, job, ad, run_agent, redis
    finally:
        jrs._run_agent, jrs._redis = saved


# Feature: adset-creative-diversity, Property 9: Validación de forma por Variant_Slot
@settings(max_examples=100, deadline=None)
@given(data=st.data(), slots=p9_slots(), kind=st.sampled_from(["copy", "image_prompt"]))
def test_variant_slot_shape_validation(data, slots, kind):
    """**Validates: Requirements 5.2, 5.3, 5.8, 14.7**"""
    import asyncio
    import copy as _copy
    import json

    from core.validation import AgentValidationError
    from services.adset_diversity import make_variant_validator
    from services.ads_validators import (
        validate_copywriter_response,
        validate_image_prompter_response,
    )
    from tests._diversity_pipeline_fakes import COPYWRITER, IMAGE_PROMPTER

    make_item = p9_copy_item if kind == "copy" else p9_prompt_item
    base = validate_copywriter_response if kind == "copy" else validate_image_prompter_response
    from services.adset_diversity import repair_variant_items

    # Slots come from build_variant_slots and always carry a Variant_Angle (Req 14.2).
    assert all(isinstance(s.get("angle"), dict) and s["angle"] for s in slots)
    slots_before = _copy.deepcopy(slots)

    items = data.draw(p9_mutated_items([make_item(s) for s in slots], slots), label="items")
    # The composite validator repairs a missing variant_key (plan_id / template_id match)
    # before the strict shape check; the oracle judges the repaired response.
    expected = p9_expected_valid(repair_variant_items(items, slots, P9_PLAN_ID)[0], slots)

    # Composite validator verdict matches the oracle (reordering is accepted).
    verdict = make_variant_validator(base, slots, P9_PLAN_ID, kind=kind)(json.dumps(items))
    assert verdict.is_valid == expected, (verdict.errors, items)

    # Req 14.7: an `angle` in the response (absent, arbitrary or the slot's own) is neither
    # read nor required → same verdict; the slots are not modified.
    angled = data.draw(p9_with_angles(items, slots), label="angled_items")
    assert p9_expected_valid(repair_variant_items(angled, slots, P9_PLAN_ID)[0], slots) == expected
    angled_verdict = make_variant_validator(base, slots, P9_PLAN_ID, kind=kind)(
        json.dumps(angled))
    assert angled_verdict.is_valid == expected, (angled_verdict.errors, angled)
    assert slots == slots_before

    # Through run_agent in the Diversity_Path: rejection → AgentValidationError, no Checkpoint.
    valid_copies = [p9_copy_item(s) for s in slots]
    valid_prompts = [p9_prompt_item(s) for s in slots]
    # Same answer on every attempt of the bounded retry.
    retries = [angled] * jrs_attempts()
    responses = (
        {COPYWRITER: retries, IMAGE_PROMPTER: [valid_prompts]} if kind == "copy"
        else {COPYWRITER: [valid_copies], IMAGE_PROMPTER: retries}
    )
    step = "copy" if kind == "copy" else "image_prompts"
    plan = {"id": P9_PLAN_ID, "concept": "c", "variants": [dict(s) for s in slots]}
    with p9_pipeline(responses, slots) as (jrs, deps, job, ad, run_agent, redis):
        key = jrs._cp_key(P9_TASK_ID, P9_AD_ID, step)
        coro = jrs._load_or_generate_copies_and_prompts(deps, ad, job, plan)
        if expected:
            copies, prompts = asyncio.run(coro)
            assert key in redis.data
            out = copies if kind == "copy" else prompts
            assert sorted(o["variant_key"] for o in out) == sorted(s["variant_key"] for s in slots)
        else:
            try:
                asyncio.run(coro)
            except AgentValidationError:
                pass
            else:
                raise AssertionError(f"expected AgentValidationError for {items!r}")
            assert key not in redis.data
            if kind == "copy":
                assert run_agent.count(IMAGE_PROMPTER) == 0
                assert jrs._cp_key(P9_TASK_ID, P9_AD_ID, "image_prompts") not in redis.data
    assert slots == slots_before


# ---------------------------------------------------------------------------
# Property 10: Merge por variant_key sin sobrescrituras
# ---------------------------------------------------------------------------

P10_AD_ID = 202
P10_PLAN_ID = f"plan_ad_{P10_AD_ID}"


def p10_copy(slot: dict) -> dict:
    key = slot["variant_key"]
    return {
        "plan_id": P10_PLAN_ID, "variant_key": key, "template_id": slot["template_id"],
        "headline": [f"H {key}"],
        "template_elements": [{"element_id": "title", "text": f"T {key}"}],
    }


def p10_prompt(slot: dict) -> dict:
    key = slot["variant_key"]
    return {
        "plan_id": P10_PLAN_ID, "variant_key": key, "template_id": slot["template_id"],
        "image_prompts": [{"element_id": "img", "image_prompt": f"P {key}"}],
    }


def p10_image(slot: dict) -> dict:
    key = slot["variant_key"]
    return {
        "variant_key": key,
        "image_prompts": [{"element_id": "img", "image_url": f"https://img/{key}",
                           "image_id": f"id-{key}"}],
    }


def p10_saved_ad(slot: dict, index: int) -> dict:
    return {"variant_key": slot["variant_key"], "ad_id": 9000 + index}


# Feature: adset-creative-diversity, Property 10: Merge por variant_key sin sobrescrituras
@settings(max_examples=100, deadline=None)
@given(data=st.data(), slots=p9_slots())
def test_merge_by_variant_key_without_overwrites(data, slots):
    """**Validates: Requirements 5.9, 8.2**"""
    from agents.tools.abyssale_tools import build_abyssale_payload
    from services.adset_diversity import (
        build_variant_proposals,
        merge_by_variant_key,
        merge_variant_creative,
    )

    slots = [dict(s) for s in slots]
    keys = [s["variant_key"] for s in slots]
    by_key = {s["variant_key"]: s for s in slots}
    plan = {"id": P10_PLAN_ID, "concept": "c", "variants": slots}

    copies = data.draw(st.permutations([p10_copy(s) for s in slots]), label="copies")
    prompts = data.draw(st.permutations([p10_prompt(s) for s in slots]), label="prompts")
    with_image = data.draw(st.lists(st.sampled_from(keys), unique=True), label="with_image")
    images = data.draw(st.permutations([p10_image(by_key[k]) for k in with_image]), label="images")
    saved_ads = data.draw(
        st.permutations([p10_saved_ad(s, i) for i, s in enumerate(slots)]), label="saved_ads")

    # Validador proposals: n items in slot order, each with its own copy / prompts.
    proposals = build_variant_proposals(plan, copies, prompts, P10_AD_ID)
    assert [p["variant_key"] for p in proposals] == keys
    for p in proposals:
        key = p["variant_key"]
        assert p["ad_id"] == P10_AD_ID and p["plan_id"] == P10_PLAN_ID
        assert p["template_id"] == by_key[key]["template_id"]
        assert p["copy"] == p10_copy(by_key[key])
        assert p["image_prompts"] == p10_prompt(by_key[key])["image_prompts"]

    # Abyssale merge: n items in slot order, copy / image / ad_channel of the same key.
    merged = merge_variant_creative(plan, copies, images, saved_ads, P10_AD_ID)
    assert [m["variant_key"] for m in merged] == keys
    for index, m in enumerate(merged):
        key = m["variant_key"]
        assert "error" not in m
        assert m["plan"]["id"] == key
        assert m["copy"] == p10_copy(by_key[key])
        assert m["image"] == (p10_image(by_key[key]) if key in with_image else {})
        assert m["ad_channel"] == p10_saved_ad(by_key[key], index)

    # Real build_abyssale_payload: one element per variant, template / plan_id of its slot.
    result = build_abyssale_payload(merged, template_id="", format_ratio="4:5")
    elements = result["payload"]["elements"]
    assert len(elements) == len(slots)
    for element, slot, index in zip(elements, slots, range(len(slots))):
        key = slot["variant_key"]
        assert element["template_id"] == slot["template_id"]
        assert element["metadata"]["plan_id"] == key
        assert element["ad_channel_id"] == 9000 + index
        assert element["layers"]["title"] == {"payload": f"T {key}"}
        if key in with_image:
            assert element["layers"]["img"] == {"image_encoded": f"https://img/{key}"}
        else:
            assert "img" not in element["layers"] and element["image_ids"] == []

    # merge_by_variant_key: regenerated keys replace, the rest keep their previous item.
    regen_keys = data.draw(st.lists(st.sampled_from(keys), unique=True), label="regen_keys")
    regenerated = [{**p10_copy(by_key[k]), "headline": ["NEW"]} for k in regen_keys]
    remerged = merge_by_variant_key(copies, regenerated, slots)
    assert [r["variant_key"] for r in remerged] == keys
    for r in remerged:
        expected_headline = ["NEW"] if r["variant_key"] in regen_keys else [f"H {r['variant_key']}"]
        assert r["headline"] == expected_headline


# ---------------------------------------------------------------------------
# Property 25: Template_Order is a deterministic permutation per seed
# ---------------------------------------------------------------------------

# Seeds: UUID4 task_ids (the real case), the empty string and arbitrary Unicode.
p25_seeds = st.one_of(
    st.uuids(version=4).map(str),
    st.just(""),
    st.text(),
)
# Project_Templates: lists without repeats, including empty and single-element.
p25_templates = st.lists(st.text(min_size=1, max_size=12), unique=True, max_size=10)


# Feature: adset-creative-diversity, Property 25: Template_Order es una permutación determinista por semilla
@settings(max_examples=100, deadline=None)
@given(templates=p25_templates, seed=p25_seeds)
def test_template_order_is_deterministic_permutation(templates, seed):
    """**Validates: Requirements 4.10, 4.11, 12.20**"""
    import random

    original = list(templates)
    state_before = random.getstate()
    first = template_order(templates, seed)
    second = template_order(templates, seed)
    state_after = random.getstate()

    # Same identifiers, in a new list, without mutating the input.
    assert sorted(first) == sorted(original)
    assert first is not templates
    assert templates == original
    # Deterministic for the same seed.
    assert first == second
    # Global `random` untouched.
    assert state_before == state_after
    if len(templates) <= 1:
        assert first == original
    else:
        # The seed actually varies the order across jobs.
        orders = {tuple(template_order(templates, f"task-{i}")) for i in range(64)}
        assert len(orders) >= 2, orders


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all adset-diversity property tests passed")
