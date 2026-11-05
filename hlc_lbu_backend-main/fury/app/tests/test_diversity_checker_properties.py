"""Property-based tests for services/diversity_checker.py (adset-creative-diversity).
Run with:
    PYTHONPATH=. pytest tests/test_diversity_checker_properties.py
    PYTHONPATH=. python -m tests.test_diversity_checker_properties
"""
import copy

from hypothesis import given, settings
from hypothesis import strategies as st

from schemas.territory_schemas import (
    BUYER_ANCHOR_CATEGORIES,
    PRODUCT_ANCHOR_CATEGORIES,
    AdDescription,
    Anchor,
    StyleAxes,
    Territory,
)
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
    anchor_side,
    check_ad_templates,
    check_territories,
    check_variant_slots,
    check_variants,
)
from services.adset_diversity import (
    build_variant_slots,
    first_text,
    slot_ad_templates,
    template_order,
)
from services.territory_assignment import AXIS_VOCAB, PALETTE_FAMILIES

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
# Small text pool so anchor texts repeat often (also across sides), wrapped in
# optional outer whitespace so repeats may differ only in case or outer spaces (Req 6.2).
_outer_ws = st.sampled_from(["", " ", "  ", "\t", "\n", " \t "])
_anchor_texts = st.builds(
    lambda pre, core, post: f"{pre}{core}{post}",
    _outer_ws,
    st.sampled_from(["envio gratis", "garantia 2 anos", "dolor de espalda", "ahorro", "Ahorro"]),
    _outer_ws,
)
_anchors = st.builds(
    Anchor,
    category=st.sampled_from(PRODUCT_ANCHOR_CATEGORIES + BUYER_ANCHOR_CATEGORIES),
    text=_anchor_texts,
)
_axes = st.builds(
    StyleAxes,
    **{axis: st.none() | st.sampled_from(vocab) for axis, vocab in AXIS_VOCAB.items()},
)
_palettes = st.none() | st.sampled_from(PALETTE_FAMILIES)


@st.composite
def _ad_descriptions(draw, slot: int) -> AdDescription:
    return AdDescription(
        ad_id=1000 + slot,
        adset_id=7,
        territory=Territory(
            anchor_primary=draw(_anchors),
            axes=draw(_axes),
            palette_family=draw(_palettes),
        ),
    )


@st.composite
def _territory_lists(draw) -> list[AdDescription]:
    # Up to 8 slots: crosses the vocabulary limits (5 and 6) in both directions.
    n = draw(st.integers(min_value=0, max_value=8))
    return [draw(_ad_descriptions(slot)) for slot in range(n)]


_pool_sizes = st.integers(min_value=0, max_value=8)


# ---------------------------------------------------------------------------
# Oracle (independent restatement of Req 6.2, 6.3, 6.10)
# ---------------------------------------------------------------------------
def _expected(territories, product_pool_size, buyer_pool_size):
    """Return (errors, warnings) as ordered lists of (code, (i, j), field, value)."""
    pools = {"product": product_pool_size, "buyer": buyer_pool_size}
    sides = [
        "product" if t.territory.anchor_primary.category in PRODUCT_ANCHOR_CATEGORIES else "buyer"
        for t in territories
    ]
    n = len(territories)
    errors, warnings = [], []
    for i in range(n):
        ti = territories[i].territory
        for j in range(i + 1, n):
            tj = territories[j].territory
            # Req 6.2: compared after strip() + casefold(); the value shown is slot i's text.
            norm_i = ti.anchor_primary.text.strip().casefold()
            if norm_i == tj.anchor_primary.text.strip().casefold():
                involved = {sides[i], sides[j]}
                exhausted = all(sides.count(s) > pools[s] for s in involved)
                item = (ANCHOR_REPEATED, (i, j), "anchor_primary.text", ti.anchor_primary.text)
                (warnings if exhausted else errors).append(item)
            for axis, vocab in AXIS_VOCAB.items():
                vi, vj = getattr(ti.axes, axis), getattr(tj.axes, axis)
                if vi is not None and vi == vj:
                    item = (AXIS_REPEATED, (i, j), axis, vi)
                    (warnings if n > len(vocab) else errors).append(item)
            if ti.palette_family is not None and ti.palette_family == tj.palette_family:
                item = (PALETTE_REPEATED, (i, j), "palette_family", ti.palette_family)
                (warnings if n > len(PALETTE_FAMILIES) else errors).append(item)
    return errors, warnings


def _assert_matches(issues, expected):
    assert [(iss.code, iss.ad_slots) for iss in issues] == [(c, s) for c, s, _, _ in expected]
    for iss, (_, (i, j), field, value) in zip(issues, expected):
        # Each issue identifies both slots, the axis (when applicable) and the value.
        assert f"Ad_Slots {i} and {j}" in iss.message
        assert repr(value) in iss.message
        assert field in iss.message
        assert iss.variant_keys == ()


# Feature: adset-creative-diversity, Property 11: Reglas de territorio del Diversity_Checker
@settings(max_examples=100, deadline=None)
@given(territories=_territory_lists(), product_pool_size=_pool_sizes, buyer_pool_size=_pool_sizes)
def test_check_territories_rules(territories, product_pool_size, buyer_pool_size):
    """**Validates: Requirements 6.1, 6.2, 6.3, 6.10**"""
    snapshot = copy.deepcopy(territories)
    result = check_territories(
        territories, product_pool_size=product_pool_size, buyer_pool_size=buyer_pool_size
    )
    exp_errors, exp_warnings = _expected(territories, product_pool_size, buyer_pool_size)

    # Exactly one issue per repeated pair, error vs warning per pool/vocabulary limit.
    _assert_matches(result.errors, exp_errors)
    _assert_matches(result.warnings, exp_warnings)
    assert result.ok == (not exp_errors)

    # Only pairs i < j, never inverted; one issue per (pair, rule, field).
    all_issues = list(result.errors) + list(result.warnings)
    assert all(i < j for i, j in (iss.ad_slots for iss in all_issues))
    keys = [(iss.code, iss.ad_slots, iss.message) for iss in all_issues]
    assert len(keys) == len(set(keys))
    # Anchors that differ only in outer whitespace / case → exactly one ANCHOR_REPEATED per pair.
    norm = [t.territory.anchor_primary.text.strip().casefold() for t in territories]
    anchor_pairs = sorted(iss.ad_slots for iss in all_issues if iss.code == ANCHOR_REPEATED)
    assert anchor_pairs == [
        (i, j) for i in range(len(norm)) for j in range(i + 1, len(norm)) if norm[i] == norm[j]
    ]

    # Pure: the input is not modified.
    assert territories == snapshot

    # Anchor side classification agrees with PRODUCT_ANCHOR_CATEGORIES membership.
    for t in territories:
        cat = t.territory.anchor_primary.category
        assert anchor_side(t.territory.anchor_primary) == (
            "product" if cat in PRODUCT_ANCHOR_CATEGORIES else "buyer"
        )

    # Req 6.1: deterministic — same input, same output.
    again = check_territories(
        territories, product_pool_size=product_pool_size, buyer_pool_size=buyer_pool_size
    )
    assert again == result
    assert list(again.errors) == list(result.errors)
    assert list(again.warnings) == list(result.warnings)
    assert territories == snapshot


# ---------------------------------------------------------------------------
# Property 12 — variant rules (Req 6.4–6.9)
# ---------------------------------------------------------------------------
_OWN_ANCHOR = "ancla propia"
# Forbidden texts: contain "xq" (never present in conforming texts) and are not
# substrings of each other.
_FORBIDDEN_POOL = ["xqa uno", "xqb dos", "xqc tres", "xqd cuatro"]
_RANK = {
    COUNT_MISMATCH: 0,
    PLAN_ID_MISMATCH: 1,
    # 6.6 and 6.7 are emitted together per collection (copies, then image prompts).
    TEMPLATE_NOT_IN_PROJECT: 2,
    TEMPLATE_MIXED_IN_AD: 2,
    COPY_REPEATED: 3,
    FORBIDDEN_TERRITORY: 4,
}
_MISSING = object()  # marker: template_id key removed


def _template_oracle(keyed, templates):
    """Independent restatement of 6.6 + 6.7 (P11: one Ad_Template per Ad).

    ``keyed`` is the ordered list of (variant_key, template_id or _MISSING).
    6.6: missing / foreign → TEMPLATE_NOT_IN_PROJECT. 6.7: every later item whose
    template differs from the first item's → TEMPLATE_MIXED_IN_AD (first key, key).
    """
    out = [(TEMPLATE_NOT_IN_PROJECT, (k,)) for k, t in keyed if t not in templates]
    if keyed:
        ref_key, ref = keyed[0]
        ref = None if ref is _MISSING else ref
        for k, t in keyed[1:]:
            if (None if t is _MISSING else t) != ref:
                out.append((TEMPLATE_MIXED_IN_AD, (ref_key, k)))
    return out


def _subset(draw, indices):
    return [i for i in indices if draw(st.booleans())]


def _pair(draw, indices):
    """Optional (a, b) with a < b drawn from ``indices``."""
    if len(indices) < 2 or not draw(st.booleans()):
        return None
    a, b = sorted(draw(st.lists(st.sampled_from(indices), min_size=2, max_size=2, unique=True)))
    return a, b


def _maybe_list(draw, text):
    # First element (list) or the value (str) — Req 6.8 / first_text.
    return [text, "otro texto"] if draw(st.booleans()) else text


@st.composite
def _variant_cases(draw):
    """Conforming plan/copies/prompts plus a random subset of injected violations.

    Returns (plan, copies, prompts, templates, n_variants, forbidden, expected_errors,
    expected_warning_count, mutated_plan, expected_slot_errors); expected errors are
    lists of (code, variant_keys).
    """
    n_templates = draw(st.integers(min_value=1, max_value=5))
    templates = [f"tpl_{t}" for t in range(n_templates)]
    n = draw(st.integers(min_value=1, max_value=6))
    ad_id = draw(st.integers(min_value=1, max_value=9999))
    ad_slot = draw(st.integers(min_value=0, max_value=7))
    plan_id = f"plan_ad_{ad_id}"
    slots = build_variant_slots(plan_id, ad_slot, n, templates)
    keys = [s["variant_key"] for s in slots]
    plan = {
        "id": plan_id,
        "target_insight": _OWN_ANCHOR,
        "_territory": {"anchor_primary": {"category": "beneficio", "text": _OWN_ANCHOR}},
        "variants": slots,
    }
    # P11: every slot shares the Ad_Template of its Ad_Slot.
    ad_template = templates[ad_slot % n_templates]
    assert all(s["template_id"] == ad_template for s in slots)
    others = [t for t in templates if t != ad_template]  # valid but foreign to this Ad
    expected: list[tuple[str, tuple[str, ...]]] = []

    def _items(kind):
        out = []
        for k, slot in enumerate(slots):
            item = {"variant_key": slot["variant_key"], "plan_id": plan_id,
                    "template_id": slot["template_id"]}
            if kind == "copy":
                item["headline"] = _maybe_list(draw, f"Titular {k}")
                item["primary_text"] = _maybe_list(draw, f"Texto principal {k}")
                if draw(st.booleans()):  # own anchor in a copy is never an error (D6)
                    item["primary_text"] = f"{_OWN_ANCHOR} y texto {k}"
            else:
                # Forbidden texts in image prompts are not checked (6.9 is copies only).
                item["prompt"] = f"escena {k} {draw(st.sampled_from(_FORBIDDEN_POOL))}"
            out.append(item)
        return out

    groups = {"copy": _items("copy"), "image_prompt": _items("image_prompt")}
    remaining: dict[str, list[int]] = {}

    # Req 6.5 — drop items (count mismatch); affected keys are the dropped ones.
    for kind, items in groups.items():
        dropped = _subset(draw, range(n)) if draw(st.booleans()) else []
        remaining[kind] = [i for i in range(n) if i not in dropped]
        groups[kind] = [items[i] for i in remaining[kind]]
        if dropped:
            expected.append((COUNT_MISMATCH, tuple(keys[i] for i in dropped)))

    for kind, items in groups.items():
        idx = list(range(len(items)))
        key_of = [items[i]["variant_key"] for i in idx]
        # Req 6.4 — wrong or missing plan_id.
        for i in _subset(draw, idx) if draw(st.booleans()) else []:
            if draw(st.booleans()):
                items[i]["plan_id"] = "plan_ad_0" if ad_id != 0 else "plan_ad_1"
            else:
                del items[i]["plan_id"]
            expected.append((PLAN_ID_MISMATCH, (key_of[i],)))
        # Req 6.7 — another valid Project_Template on some items (mixed in the Ad).
        if others and draw(st.booleans()):
            for i in _subset(draw, idx):
                items[i]["template_id"] = draw(st.sampled_from(others))
        # Req 6.6 — foreign or missing template (also mixes the Ad, rule 6.7).
        for i in _subset(draw, idx) if draw(st.booleans()) else []:
            if draw(st.booleans()):
                items[i]["template_id"] = f"tpl_foreign_{i}"
            else:
                del items[i]["template_id"]
        expected.extend(_template_oracle(
            [(key_of[i], items[i].get("template_id", _MISSING)) for i in idx], templates))

    copies = groups["copy"]
    cidx = list(range(len(copies)))
    ckey = [c["variant_key"] for c in copies]
    # Req 6.8 — identical first headline and primary_text (whitespace / case variants).
    same = _pair(draw, cidx)
    if same:
        a, b = same
        for field in ("headline", "primary_text"):
            text = first_text(copies[a][field])
            copies[b][field] = _maybe_list(draw, f"  {text.upper()} ")
        expected.append((COPY_REPEATED, (ckey[a], ckey[b])))
    else:
        # Only the headline repeated → not a 6.8 violation.
        pair = _pair(draw, cidx)
        if pair:
            copies[pair[1]]["headline"] = first_text(copies[pair[0]]["headline"]).lower()

    # Req 6.8 — empty / None / missing values never match: two copies whose first
    # headline and/or primary_text are empty (the other field equal and non-empty).
    empty_pair = _pair(draw, [i for i in cidx if not same or i not in same])
    if empty_pair:
        empty_fields = draw(st.sampled_from(
            [("headline",), ("primary_text",), ("headline", "primary_text")]))
        for i in empty_pair:
            for field in ("headline", "primary_text"):
                if field not in empty_fields:
                    copies[i][field] = _maybe_list(draw, "Mismo texto vacio")
                    continue
                value = draw(st.sampled_from(["", "   ", None, [], [""], [" \n"], _MISSING]))
                if value is _MISSING:
                    del copies[i][field]
                else:
                    copies[i][field] = value

    # Req 6.9 — forbidden texts as substrings; noise: empty, duplicates, own anchor.
    forbidden_used = draw(st.lists(st.sampled_from(_FORBIDDEN_POOL), unique=True, max_size=4))
    forbidden = list(forbidden_used)
    forbidden += draw(st.lists(st.sampled_from(["", "   ", "\n"]), max_size=2))
    forbidden += [f" {t.upper()} " for t in forbidden_used if draw(st.booleans())]
    own_in_forbidden = draw(st.booleans())
    if own_in_forbidden:
        forbidden.append(f"  {_OWN_ANCHOR.upper()} ")
    forbidden = draw(st.permutations(forbidden))
    forbidden_fields: dict[str, str] = {}  # variant_key → field(s) named in the 6.9 message
    if forbidden_used:
        excluded = set(same or ()) | set(empty_pair or ())
        free = [i for i in cidx if i not in excluded]
        for i in _subset(draw, free):
            text = draw(st.sampled_from(forbidden_used))
            fields = draw(st.sampled_from(
                [("headline",), ("primary_text",), ("headline", "primary_text")]))
            for field in fields:
                copies[i][field] = f"{first_text(copies[i].get(field))} con {text.upper()}"
            expected.append((FORBIDDEN_TERRITORY, (ckey[i],)))
            forbidden_fields[ckey[i]] = " and ".join(fields)

    # Items without variant_key take the slot key at the same index (no drops only).
    for kind, items in groups.items():
        if len(remaining[kind]) == n and draw(st.booleans()):
            for i in _subset(draw, range(n)):
                del items[i]["variant_key"]

    # check_variant_slots on a mutated copy of the plan's slots (6.6 / 6.7).
    mutated = copy.deepcopy(plan)
    mslots = mutated["variants"]
    if others and draw(st.booleans()):
        for i in _subset(draw, list(range(n))):
            mslots[i]["template_id"] = draw(st.sampled_from(others))
    for i in _subset(draw, list(range(n))):
        mslots[i]["template_id"] = f"tpl_foreign_slot_{i}"
    slot_expected = _template_oracle(
        [(s["variant_key"], s["template_id"]) for s in mslots], templates)

    return (plan, copies, groups["image_prompt"], templates, n, forbidden, expected,
            int(own_in_forbidden), mutated, slot_expected, forbidden_fields)


def _codes_keys(issues):
    return sorted((iss.code, iss.variant_keys) for iss in issues)


# Feature: adset-creative-diversity, Property 12: Reglas de variantes del Diversity_Checker
@settings(max_examples=100, deadline=None)
@given(case=_variant_cases())
def test_check_variants_rules(case):
    """**Validates: Requirements 6.1, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9**"""
    (plan, copies, prompts, templates, n, forbidden, expected, n_warnings,
     mutated, slot_expected, forbidden_fields) = case
    snapshot = copy.deepcopy((plan, copies, prompts, forbidden))

    result = check_variants(plan, copies, prompts, project_templates=templates,
                            n_variants=n, forbidden=forbidden)

    # Exactly the injected violations, each with its affected variant_key(s).
    assert _codes_keys(result.errors) == sorted(expected)
    assert result.ok == (not expected)
    assert result.failing_variant_keys() == {k for _, ks in expected for k in ks}
    # Stable rule order: 6.5, 6.4, 6.6/6.7 (per collection), 6.8, 6.9.
    ranks = [_RANK[iss.code] for iss in result.errors]
    assert ranks == sorted(ranks)
    counts = {"copies": len(copies), "image prompts": len(prompts)}
    for iss in result.errors:
        if iss.code == COUNT_MISMATCH:
            # Expected and received numbers (Req 6.5).
            assert f"Ad {plan['id']!r}: " in iss.message
            assert any(f"expected {n} {label}, got {got}" in iss.message
                       for label, got in counts.items())
            continue
        if iss.code == TEMPLATE_MIXED_IN_AD:
            # P11: names the Ad, both variant_key and both template_id.
            assert f"Ad {plan['id']!r}: " in iss.message
        for key in iss.variant_keys:
            assert key in iss.message
        if iss.code == FORBIDDEN_TERRITORY:
            assert any(t in iss.message.casefold() for t in _FORBIDDEN_POOL)
            # Req 6.9: the message names the field(s) containing the forbidden text.
            (key,) = iss.variant_keys
            assert f"copy {key}: {forbidden_fields[key]} contain" in iss.message

    # 6.7 is always an error, never a warning, for any n_variants / len(Project_Templates).
    assert TEMPLATE_MIXED_IN_AD not in {w.code for w in result.warnings}

    # D6: empty forbidden texts never error; own anchor → one warning, no error.
    assert [w.code for w in result.warnings] == [FORBIDDEN_IS_OWN_ANCHOR] * n_warnings
    assert all(w.variant_keys == () for w in result.warnings)

    # Pure and deterministic (Req 6.1).
    assert (plan, copies, prompts, forbidden) == snapshot
    again = check_variants(plan, copies, prompts, project_templates=templates,
                           n_variants=n, forbidden=forbidden)
    assert again == result

    # check_variant_slots: valid slots pass; mutated slots report exactly the injections.
    assert check_variant_slots(plan, templates, n).errors == ()
    slot_result = check_variant_slots(mutated, templates, n)
    assert _codes_keys(slot_result.errors) == sorted(slot_expected)
    assert slot_result.warnings == ()
    assert check_variant_slots(mutated, templates, n) == slot_result


# Arbitrary `angle` values: vocabulary-like ids, free text, empty, None, non-strings.
_angle_values = st.one_of(
    st.sampled_from(["dolor", "beneficio", "prueba_social", "urgencia", "comparativa"]),
    st.text(max_size=20),
    st.none(),
    st.integers(),
    st.lists(st.text(max_size=5), max_size=2),
)


def _with_angles(draw, items):
    """Deep copy of ``items`` with an arbitrary `angle` key on a random subset."""
    out = copy.deepcopy(items)
    for item in out:
        if draw(st.booleans()):
            item["angle"] = draw(_angle_values)
    return out


# Feature: adset-creative-diversity, Property 12: Reglas por Ad del Diversity_Checker
@settings(max_examples=100, deadline=None)
@given(case=_variant_cases(), data=st.data())
def test_check_variants_ignores_angle_in_copies(case, data):
    """**Validates: Requirements 6.1, 14.8**"""
    (plan, copies, prompts, templates, n, forbidden, *_rest) = case
    baseline = check_variants(plan, copies, prompts, project_templates=templates,
                              n_variants=n, forbidden=forbidden)

    # Req 14.8: the angle is not verified on the text, so adding it changes nothing.
    angled_copies = _with_angles(data.draw, copies)
    angled_prompts = _with_angles(data.draw, prompts)
    snapshot = copy.deepcopy((plan, angled_copies, angled_prompts, forbidden))
    result = check_variants(plan, angled_copies, angled_prompts, project_templates=templates,
                            n_variants=n, forbidden=forbidden)

    assert result == baseline
    assert list(result.errors) == list(baseline.errors)
    assert list(result.warnings) == list(baseline.warnings)
    # Pure and deterministic (Req 6.1).
    assert (plan, angled_copies, angled_prompts, forbidden) == snapshot
    assert check_variants(plan, angled_copies, angled_prompts, project_templates=templates,
                          n_variants=n, forbidden=forbidden) == result


# ---------------------------------------------------------------------------
# Property 24 — Ad_Templates between Ad_Slots (Req 4.6, 6.10, 6.12)
# ---------------------------------------------------------------------------

# Distinct ids, as returned by resolve_project_templates (deduplicated).
_project_templates = st.lists(
    st.sampled_from([f"tpl_{t}" for t in range(8)]), min_size=1, max_size=8, unique=True
)


def _check_ad_templates_oracle(slot_templates, project_templates):
    """Pairs i < j sharing a template; error if n_slots <= len(templates), else warning."""
    n = len(slot_templates)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)
             if slot_templates[i] == slot_templates[j]]
    return pairs, n > len(project_templates)


def _assert_ad_template_issues(result, slot_templates, project_templates):
    pairs, exhausted = _check_ad_templates_oracle(slot_templates, project_templates)
    issues = result.warnings if exhausted else result.errors
    other = result.errors if exhausted else result.warnings
    assert other == ()
    assert [iss.ad_slots for iss in issues] == pairs
    for iss, (i, j) in zip(issues, pairs):
        assert iss.code == AD_TEMPLATE_REPEATED
        assert f"Ad_Slots {i} and {j}" in iss.message
        assert repr(slot_templates[i]) in iss.message
        assert iss.variant_keys == ()
    assert result.ok == (exhausted or not pairs)


# Feature: adset-creative-diversity, Property 24: Reparto de Ad_Templates entre Ad_Slots
@settings(max_examples=100, deadline=None)
@given(templates=_project_templates, n_slots=st.integers(min_value=1, max_value=20),
       task_id=st.one_of(st.uuids().map(str), st.text(min_size=1, max_size=40)))
def test_slot_ad_templates_distribution(templates, n_slots, task_id):
    """**Validates: Requirements 4.6, 6.1, 6.10, 6.12**"""
    snapshot = list(templates)
    # Template_Order of the job (P12): a permutation of the Project_Templates seeded
    # with task_id; the Diversity_Path passes it to slot_ad_templates.
    order = template_order(templates, task_id)
    assert sorted(order) == sorted(templates)
    assert template_order(templates, task_id) == order
    assigned = slot_ad_templates(n_slots, order)
    assert assigned == [order[s % len(order)] for s in range(n_slots)]
    assert templates == snapshot

    # 6.12 compares against the Project_Templates; the permutation keeps len unchanged.
    result = check_ad_templates(assigned, templates)
    if n_slots <= len(templates):
        # Enough templates: every Ad gets a different one; nothing to report (6.12).
        assert len(set(assigned)) == n_slots
        assert result.errors == () and result.warnings == ()
        assert result.ok
    else:
        # Exhausted: rotation (s and s + len share) → warnings only (6.10), never 6.12 errors.
        for s in range(n_slots - len(order)):
            assert assigned[s] == assigned[s + len(order)]
        assert result.errors == ()
        assert result.warnings
        assert result.ok
    _assert_ad_template_issues(result, assigned, templates)
    assert templates == snapshot


# Feature: adset-creative-diversity, Property 24: Reparto de Ad_Templates entre Ad_Slots
@settings(max_examples=100, deadline=None)
@given(data=st.data(), templates=_project_templates)
def test_check_ad_templates_arbitrary_maps(data, templates):
    """**Validates: Requirements 4.6, 6.10, 6.12**"""
    n_slots = data.draw(st.integers(min_value=0, max_value=12))
    # Arbitrary slot → template map, drawn from a small pool so repetitions are frequent.
    pool = templates + ["tpl_x"]
    slot_templates = data.draw(st.lists(st.sampled_from(pool), min_size=n_slots,
                                        max_size=n_slots))
    # Inject at least one repetition when possible.
    if n_slots >= 2 and data.draw(st.booleans()):
        i, j = sorted(data.draw(st.lists(st.integers(0, n_slots - 1), min_size=2,
                                         max_size=2, unique=True)))
        slot_templates[j] = slot_templates[i]
    snapshot = (list(slot_templates), list(templates))

    result = check_ad_templates(slot_templates, templates)
    _assert_ad_template_issues(result, slot_templates, templates)

    # Pure and deterministic.
    assert (slot_templates, templates) == snapshot
    assert check_ad_templates(slot_templates, templates) == result
    assert check_ad_templates(tuple(slot_templates), tuple(templates)) == result


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all diversity-checker property tests passed")
