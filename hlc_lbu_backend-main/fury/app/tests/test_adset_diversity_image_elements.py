"""Property-based test for the Image_Elements extraction (adset-creative-diversity,
P15, task 35.4): ``services.adset_diversity.template_image_elements``.

Pure function, no network, Redis nor settings. Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_image_elements.py
"""
import copy
import json

from hypothesis import given, settings
from hypothesis import strategies as st

from services.adset_diversity import template_image_elements

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

_ABSENT = object()  # marker: key not present in the element dict

_TYPES = st.sampled_from(
    ["image", "Image", "IMAGE", "text", "logo", "button", "container", "shape", None, _ABSENT]
)

# Ids biased towards realistic names (so patterns and repeats actually hit) plus
# arbitrary strings and ints.
_ID_TEXT = st.one_of(
    st.sampled_from([
        "image_0", "image_1", "Image_Main", "degradado_top", "Degradado_Bottom",
        "Gradient_Top", "OVERLAY_1", "mask", "shape_bg", "hook", "tagline", "logo_0",
        "root", " ", "x",
    ]),
    st.text(max_size=12),
)
_ID_VALUE = st.one_of(
    st.just(_ABSENT), st.none(), st.just(""), _ID_TEXT,
    st.integers(min_value=-5, max_value=1000),
)


@st.composite
def _element(draw):
    el = {}
    t = draw(_TYPES)
    if t is not _ABSENT:
        el["type"] = t
    for key in ("name", "id"):
        v = draw(_ID_VALUE)
        if v is not _ABSENT:
            el[key] = v
    if draw(st.booleans()):
        el["layout"] = {"1080x1080": {"width": 1080, "height": 1080}}
    return el


_NON_DICT = st.one_of(
    st.none(), st.integers(), st.text(max_size=8),
    st.lists(st.integers(), max_size=2), st.tuples(st.just("type"), st.just("image")),
)


@st.composite
def _template(draw):
    base = draw(st.lists(st.one_of(_element(), _NON_DICT), max_size=12))
    # Force some repeated Element_Ids by duplicating random dict elements.
    dicts = [e for e in base if isinstance(e, dict)]
    if dicts and draw(st.booleans()):
        for _ in range(draw(st.integers(min_value=1, max_value=3))):
            dup = copy.deepcopy(draw(st.sampled_from(dicts)))
            base.insert(draw(st.integers(min_value=0, max_value=len(base))), dup)
    return {"id": "tpl", "name": "Template", "elements": base}


_PATTERN = st.one_of(
    st.sampled_from([
        "", " ", "   ", "\t", "degradado", "Degradado", " GRADIENT ", "overlay",
        "Mask", "SHAPE", "image", "IMAGE_0", "hook",
    ]),
    st.text(max_size=6),
)
_PATTERNS = st.lists(_PATTERN, max_size=6)


# ---------------------------------------------------------------------------
# Independent oracle (written from Req 15.2, not from the implementation)
# ---------------------------------------------------------------------------

def _oracle_element_id(el: dict) -> str:
    name = el["name"] if "name" in el else None
    chosen = name if name else (el["id"] if "id" in el else None)
    return str(chosen) if chosen else ""


def _image_ids(template: dict) -> list[str]:
    """Non-empty Element_Ids of dict elements with ``type == "image"``, in order."""
    out = []
    for el in template["elements"]:
        if type(el) is dict and "type" in el and el["type"] == "image":
            eid = _oracle_element_id(el)
            if eid != "":
                out.append(eid)
    return out


def _oracle(template: dict, patterns: list[str]) -> list[str]:
    active = [p.strip().casefold() for p in patterns if p.strip() != ""]
    expected: list[str] = []
    for eid in _image_ids(template):
        if any(p in eid.casefold() for p in active):
            continue
        if eid not in expected:
            expected.append(eid)
    return expected


# ---------------------------------------------------------------------------
# Property 29
# ---------------------------------------------------------------------------

# Feature: adset-creative-diversity, Property 29: Extracción de Image_Elements según oráculo
@settings(max_examples=100, deadline=None)
@given(template=_template(), patterns=_PATTERNS)
def test_template_image_elements_matches_oracle(template, patterns):
    """**Validates: Requirements 15.2, 12.29, 12.35**"""
    template_before = copy.deepcopy(template)
    patterns_before = copy.deepcopy(patterns)

    result = template_image_elements(template, patterns)

    # Exact oracle match (order, filtering, first occurrence).
    assert result == _oracle(template_before, patterns_before)
    # No repeats and subset of the ``image`` Element_Ids.
    assert len(result) == len(set(result))
    assert set(result) <= set(_image_ids(template_before))
    assert all(isinstance(eid, str) and eid for eid in result)
    # Idempotent and non-mutating.
    assert template_image_elements(template, patterns) == result
    assert template == template_before
    assert patterns == patterns_before


# ---------------------------------------------------------------------------
# Property 30: Image_Elements_Checker
# ---------------------------------------------------------------------------

_IE_ID = st.one_of(
    st.sampled_from([
        "image_0", "image_1", "Image_Main", "IMAGE", "foto", "bg_photo", "x", " a ",
        "producto_1", "Image 2",
    ]),
    st.text(min_size=1, max_size=70),  # long ones exercise the repr truncation
)
_IMAGE_ELEMENTS = st.lists(_IE_ID, unique=True, max_size=6)

_VARIANT_KEY = st.one_of(
    st.sampled_from(["ad0-v0", "ad0-v1", "ad1-v0", "k"]),
    st.text(max_size=70),
    st.none(), st.integers(), st.just(_ABSENT),
)
_ARBITRARY = st.recursive(
    st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=6)),
    lambda inner: st.one_of(
        st.lists(inner, max_size=3),
        st.dictionaries(
            st.sampled_from(["element_id", "element_type", "prompt", "x"]), inner, max_size=3
        ),
    ),
    max_leaves=6,
)
_MUTATIONS = st.sampled_from([
    "remove", "add", "repeat", "rename", "upper", "spaces", "type_change", "type_remove",
    "non_list", "non_dict", "drop_key",
])


@st.composite
def _variant(draw, expected):
    """A conforming Image_Prompter variant perturbed by 0..3 mutations."""
    order = draw(st.permutations(expected))
    prompts = [
        {"element_id": e, "element_type": "image", "prompt": f"photo of {e}"} for e in order
    ]
    item: dict = {"image_prompts": prompts}
    vk = draw(_VARIANT_KEY)
    if vk is not _ABSENT:
        item["variant_key"] = vk
    if draw(st.integers(min_value=0, max_value=3)) == 0:
        return item  # conforming as-is (roughly 1 in 4)
    for mutation in draw(st.lists(_MUTATIONS, min_size=1, max_size=3)):
        current = item.get("image_prompts")
        if mutation == "non_list":
            item["image_prompts"] = draw(st.one_of(
                st.none(), st.integers(), st.text(max_size=6),
                st.dictionaries(st.text(max_size=3), st.integers(), max_size=2),
                st.tuples(st.just({"element_id": "image_0", "element_type": "image"})),
            ))
            continue
        if mutation == "drop_key":
            item.pop("image_prompts", None)
            continue
        if not isinstance(current, list):
            continue
        dict_idx = [i for i, el in enumerate(current) if isinstance(el, dict)]
        if mutation == "add":
            new_id = draw(st.one_of(_IE_ID, st.none(), st.integers()))
            current.insert(
                draw(st.integers(0, len(current))),
                {"element_id": new_id, "element_type": "image", "prompt": "extra"},
            )
        elif mutation == "non_dict":
            current.insert(draw(st.integers(0, len(current))), draw(st.one_of(
                st.none(), st.integers(), st.text(max_size=6), st.lists(st.integers(), max_size=2),
            )))
        elif not dict_idx:
            continue
        else:
            i = draw(st.sampled_from(dict_idx))
            el = current[i]
            if mutation == "remove":
                current.pop(i)
            elif mutation == "repeat":
                current.insert(draw(st.integers(0, len(current))), copy.deepcopy(el))
            elif mutation == "rename":
                el["element_id"] = draw(st.one_of(_IE_ID, st.none(), st.integers()))
            elif mutation == "upper" and isinstance(el.get("element_id"), str):
                el["element_id"] = el["element_id"].upper()
            elif mutation == "spaces" and isinstance(el.get("element_id"), str):
                el["element_id"] = draw(st.sampled_from([" ", "  ", "\t"])) + el["element_id"]
            elif mutation == "type_change":
                el["element_type"] = draw(st.sampled_from(["Image", "IMAGE", "text", "", None, 1]))
            elif mutation == "type_remove":
                el.pop("element_type", None)
    return item


@st.composite
def _items(draw):
    expected = draw(_IMAGE_ELEMENTS)
    kind = draw(st.integers(min_value=0, max_value=9))
    if kind == 0:  # fully arbitrary response
        return expected, draw(_ARBITRARY)
    items = draw(st.lists(
        st.one_of(_variant(expected), _variant(expected), _ARBITRARY), max_size=4
    ))
    return expected, items


def _p30_shown(value) -> str:
    """Independent restatement of the D25 display format."""
    if isinstance(value, str):
        text = repr(value)
        return text if len(text) <= 64 else text[:61] + "..."
    return f"<{type(value).__name__}>"


def _p30_shown_list(values) -> str:
    shown = [_p30_shown(v) for v in values[:20]]
    if len(values) > 20:
        shown.append(f"... (+{len(values) - 20} more)")
    return "[" + ", ".join(shown) + "]"


def _p30_conforms(item: dict, expected: list[str]) -> bool:
    prompts = item["image_prompts"] if "image_prompts" in item else None
    if type(prompts) is not list or not all(type(el) is dict for el in prompts):
        return False
    ids = [el["element_id"] if "element_id" in el else None for el in prompts]
    if not all(type(i) is str for i in ids) or sorted(ids) != sorted(expected):
        return False
    return all("element_type" in el and el["element_type"] == "image" for el in prompts)


def _p30_received(item: dict) -> list:
    prompts = item.get("image_prompts")
    if type(prompts) is not list:
        return []
    return [
        el.get("element_id") if type(el) is dict else _NonDictShown(el) for el in prompts
    ]


class _NonDictShown(str):
    """Non-dict elements are shown only by their type (even a ``str``)."""

    def __new__(cls, value):
        return super().__new__(cls, f"<{type(value).__name__}>")


def _p30_received_shown(item: dict) -> str:
    received = _p30_received(item)
    shown = [
        str(v) if isinstance(v, _NonDictShown) else _p30_shown(v) for v in received[:20]
    ]
    if len(received) > 20:
        shown.append(f"... (+{len(received) - 20} more)")
    return "[" + ", ".join(shown) + "]"


# Feature: adset-creative-diversity, Property 30: Oráculo del Image_Elements_Checker
@settings(max_examples=100, deadline=None)
@given(data=_items())
def test_check_image_elements_matches_oracle(data):
    """**Validates: Requirements 15.5, 12.31, 12.35**"""
    from services.adset_diversity import check_image_elements

    expected, items = data
    items_before = copy.deepcopy(items)
    expected_before = list(expected)

    errors = check_image_elements(items, expected)

    assert isinstance(errors, list) and all(isinstance(e, str) for e in errors)
    if not isinstance(items_before, list):
        assert errors == []
    else:
        failing = [
            it for it in items_before
            if isinstance(it, dict) and not _p30_conforms(it, expected_before)
        ]
        # [] iff every variant conforms; otherwise exactly one error per failing variant.
        assert (errors == []) == (failing == [])
        assert len(errors) == len(failing)
        for err, it in zip(errors, failing):
            prefix = (
                f"Image prompt {_p30_shown(it.get('variant_key'))}: element_ids "
                f"{_p30_received_shown(it)} do not match Image_Elements "
                f"{_p30_shown_list(expected_before)} ("
            )
            assert err.startswith(prefix), (err, prefix)
            for eid in expected_before:
                assert _p30_shown(eid) in err
    # Non-mutating.
    assert items == items_before
    assert expected == expected_before


# ---------------------------------------------------------------------------
# Property 31: composite validator with Image_Elements
# ---------------------------------------------------------------------------
P31_PLAN_ID = "plan_ad_102"
P31_SHAPE_MUTATIONS = (
    "delete", "duplicate", "reorder", "change_plan_id", "change_variant_key",
    "drop_variant_key", "change_template_id", "empty",
)
@st.composite
def _p31_slots(draw):
    from services.adset_diversity import build_variant_slots
    templates = draw(st.lists(st.sampled_from(["tA", "tB", "tC"]), min_size=1, max_size=3,
                              unique=True))
    return build_variant_slots(
        P31_PLAN_ID, ad_slot=draw(st.integers(0, 4)),
        n_variants=draw(st.integers(1, 4)), project_templates=templates,
    )
def _p31_shape_mutate(draw, items: list, slots: list[dict]) -> list:
    """Property 9 shape faults on ``plan_id`` / ``variant_key`` / ``template_id``."""
    keys = [s["variant_key"] for s in slots]
    for op in draw(st.lists(st.sampled_from(P31_SHAPE_MUTATIONS), max_size=3)):
        if op == "empty":
            items = []
            continue
        dict_idx = [i for i, it in enumerate(items) if isinstance(it, dict)]
        if not dict_idx:
            continue
        i = draw(st.sampled_from(dict_idx))
        if op == "delete":
            items.pop(i)
        elif op == "duplicate":
            items.insert(i, copy.deepcopy(items[i]))
        elif op == "reorder":
            items = list(draw(st.permutations(items)))
        elif op == "change_plan_id":
            items[i]["plan_id"] = draw(st.sampled_from(["plan_ad_999", P31_PLAN_ID + "x"]))
        elif op == "change_variant_key":
            items[i]["variant_key"] = draw(st.sampled_from(keys + [f"{P31_PLAN_ID}_v99"]))
        elif op == "drop_variant_key":
            items[i].pop("variant_key", None)
        elif op == "change_template_id":
            items[i]["template_id"] = draw(st.sampled_from(["tA", "tB", "tC", "tZ"]))
    return items
@st.composite
def _p31_case(draw):
    """``(slots, image_elements, response_text)``: Property 30 perturbations of the
    ``image_prompts`` plus shape faults, or an arbitrary JSON response."""
    slots = draw(_p31_slots())
    expected = draw(_IMAGE_ELEMENTS)
    if draw(st.integers(0, 14)) == 0:
        return slots, expected, json.dumps(draw(_ARBITRARY))
    items: list = []
    for slot in slots:
        variant = draw(_variant(expected))  # Property 30 generator
        item = {"plan_id": P31_PLAN_ID, "variant_key": slot["variant_key"],
                "template_id": slot["template_id"]}
        if "image_prompts" in variant:
            item["image_prompts"] = variant["image_prompts"]
        items.append(item)
    if draw(st.integers(0, 5)) == 0:
        items.insert(draw(st.integers(0, len(items))), draw(_ARBITRARY))
    items = _p31_shape_mutate(draw, items, slots)
    return slots, expected, json.dumps(items)
def _p31_copy_item(slot: dict) -> dict:
    return {
        "plan_id": P31_PLAN_ID, "variant_key": slot["variant_key"],
        "template_id": slot["template_id"], "headline": ["H"], "primary_text": ["P"],
        "description": ["D"], "cta": ["LEARN_MORE"],
        "template_elements": [{"element_id": "title", "text": "H"}],
    }
def _p31_pre_p15(base, slots, plan_id, kind, response):
    """Reference composite validator as it was before P15 (normalize → base → repair →
    check_variant_items), plus the repaired data even when the shape check fails."""
    from core.validation import ValidationResult
    from services.adset_diversity import (
        check_variant_items, normalize_variant_fields, repair_variant_items,
    )
    normalized, _ = normalize_variant_fields(response, kind=kind)
    result = base(normalized)
    if not result.is_valid:
        return result, None
    data, repairs = repair_variant_items(result.data, slots, plan_id)
    warnings = list(result.warnings) + repairs
    errors = check_variant_items(data, slots, plan_id, kind=kind)
    if errors:
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings, data=None,
                                error_code="ERR_VARIANT_SHAPE"), data
    return ValidationResult(is_valid=True, errors=list(result.errors), warnings=warnings,
                            data=data, error_code=result.error_code), data
def _p31_view(result) -> tuple:
    return (result.is_valid, result.errors, result.warnings, result.data, result.error_code)
def _p31_element_ids(items: list) -> list:
    out = []
    for it in items:
        prompts = it.get("image_prompts")
        prompts = [prompts] if isinstance(prompts, dict) else prompts  # normalize_variant_fields
        out.append([el.get("element_id") for el in prompts])
    return out
async def _p31_run_agent(validator, response_text: str):
    """``run_agent`` semantics (FakeRunAgent, as in Property 9) for one attempt."""
    from tests._diversity_pipeline_fakes import IMAGE_PROMPTER, FakeRunAgent
    class _Agent:
        name = IMAGE_PROMPTER
    run_agent = FakeRunAgent({IMAGE_PROMPTER: [response_text]})
    return await run_agent(_Agent(), "user", "message", validator=validator)
# Feature: adset-creative-diversity, Property 31: Validador compuesto con Image_Elements
@settings(max_examples=100, deadline=None)
@given(case=_p31_case(), data=st.data())
def test_composite_validator_with_image_elements(case, data):
    """**Validates: Requirements 15.6, 15.7, 12.31**"""
    import asyncio
    from core.validation import AgentValidationError
    from services.adset_diversity import check_image_elements, make_variant_validator
    from services.ads_validators import (
        validate_copywriter_response, validate_image_prompter_response,
    )
    slots, expected, response = case
    slots_before = copy.deepcopy(slots)
    expected_before = list(expected)
    base = validate_image_prompter_response
    old, repaired = _p31_pre_p15(base, slots, P31_PLAN_ID, "image_prompt", response)
    # image_elements=None keeps the pre-P15 behaviour exactly.
    none_result = make_variant_validator(base, slots, P31_PLAN_ID, kind="image_prompt",
                                         image_elements=None)(response)
    assert _p31_view(none_result) == _p31_view(old)
    validator = make_variant_validator(base, slots, P31_PLAN_ID, kind="image_prompt",
                                       image_elements=expected)
    result = validator(response)
    ie_errors = (check_image_elements(repaired, expected_before)
                 if isinstance(repaired, list) else [])
    # Accepts iff the validator without Image_Elements accepts and the checker gives [].
    assert result.is_valid == (old.is_valid and ie_errors == []), (result.errors, response)
    if repaired is None:
        # The base validator rejected it: unchanged result, no Image_Elements check.
        assert _p31_view(result) == _p31_view(old)
    elif not result.is_valid:
        # Shape and/or Image_Elements rejection: ERR_VARIANT_SHAPE with both groups.
        shape_errors = [] if old.is_valid else old.errors
        assert result.error_code == "ERR_VARIANT_SHAPE"
        assert result.errors == shape_errors + ie_errors
        assert result.data is None
    else:
        assert _p31_view(result) == _p31_view(old)
        # element_ids are exactly those of the response (none invented/renamed/removed).
        assert _p31_element_ids(result.data) == _p31_element_ids(json.loads(response))
    # Through run_agent: rejection → AgentValidationError with the same code and errors.
    try:
        returned = asyncio.run(_p31_run_agent(validator, response))
    except AgentValidationError as exc:
        assert not result.is_valid
        assert exc.code == result.error_code
        assert exc.errors == result.errors
    else:
        assert result.is_valid
        assert returned == result.data
    # kind="copy" without Image_Elements: identical to the pre-P15 validator.
    copies = _p31_shape_mutate(data.draw, [_p31_copy_item(s) for s in slots], slots)
    copy_text = json.dumps(copies)
    copy_old, _ = _p31_pre_p15(validate_copywriter_response, slots, P31_PLAN_ID, "copy",
                               copy_text)
    for kwargs in ({}, {"image_elements": None}):
        copy_result = make_variant_validator(validate_copywriter_response, slots, P31_PLAN_ID,
                                             kind="copy", **kwargs)(copy_text)
        assert _p31_view(copy_result) == _p31_view(copy_old)
    # Neither the slots nor the Image_Elements are mutated.
    assert slots == slots_before
    assert expected == expected_before


# ---------------------------------------------------------------------------
# Property 32: Image_Elements line in the message to the Image_Prompter
# ---------------------------------------------------------------------------
P32_PLAN_ID = "plan_ad_101"
P32_CTX_JSON = json.dumps({"adset": {"id": 7, "name": "Adset"}})
P32_SIGNATURE_MARKERS = ("X-Amz-Signature", "X-Amz-Credential", "Expires", "X-Amz-")
P32_PLAN = {
    "id": P32_PLAN_ID, "concept": "Concepto", "emocion": "calma", "intencion": None,
    "visual_dominante": None, "contexto_uso": None, "psicologia": None, "tone": "hook",
    "color_palette": "cálida", "target_insight": "insight",
    "_territory": {"territorio_prohibido": ["otro"]},
    "_project_templates": ["tA", "tB"],
}
# Image Element_Ids that no Decorative_Image_Pattern matches (so 0..6 survive).
_P32_IDS = st.one_of(
    st.sampled_from(["image_0", "image_1", "bg_image", "picture", "background", "foto",
                     "Image Main", "producto_1", "ñandú"]),
    st.integers(min_value=0, max_value=99).map(lambda n: f"photo_{n}"),
)
_P32_BASE_URL = st.sampled_from([
    "https://bucket.s3.amazonaws.com/previews/tpl.png",
    "https://cdn.example.com/a/b/preview.jpg",
])
_P32_QUERY = st.sampled_from([
    "",
    "?X-Amz-Signature=abc123&X-Amz-Credential=AKIA%2F20240101",
    "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA&X-Amz-Signature=deadbeef",
    "?Expires=1700000000&Signature=xyz&Key-Pair-Id=K1",
    "?X-Amz-Credential=c&Expires=60",
])


@st.composite
def _p32_template(draw):
    """``(template_id, template, expected_payload)`` with an independent expectation."""
    ids = draw(st.lists(_P32_IDS, unique=True, max_size=6))
    elements: list = []
    expected_elements = []
    for eid in ids:
        el: dict = {"type": "image", "name": eid}
        exp: dict = {"element_id": eid}
        if draw(st.booleans()):
            w, h = draw(st.integers(1, 4000)), draw(st.integers(1, 4000))
            el["layout"] = {"instagram-portrait": {"x": 0, "y": 0, "width": w, "height": h}}
            exp.update(width=w, height=h)
        elif draw(st.booleans()):  # invalid / other-format dimensions: no width/height
            el["layout"] = draw(st.sampled_from([
                {"instagram-portrait": {"width": 0, "height": 100}},
                {"instagram-portrait": {"width": True, "height": 100}},
                {"instagram-portrait": {"width": 100}},
                {"facebook-feed": {"width": 100, "height": 100}},
            ]))
        elements.append(el)
        expected_elements.append(exp)
    # Text layers and decorative images interleaved: never Image_Elements.
    for extra in draw(st.lists(st.sampled_from([
        {"type": "text", "name": "hook"}, {"type": "text", "name": "tagline"},
        {"type": "image", "name": "degradado_top"}, {"type": "image", "name": "overlay_1"},
    ]), max_size=3)):
        elements.insert(draw(st.integers(0, len(elements))), dict(extra))
    template: dict = {"id": "tpl", "name": "Template", "elements": elements}
    base = draw(_P32_BASE_URL)
    url = base + draw(_P32_QUERY)
    where = draw(st.sampled_from(["absent", "top", "formats"]))
    expected_url = None
    if where == "top":
        template["preview_url"] = url
        expected_url = base
    elif where == "formats":
        template["formats"] = [
            {"id": "facebook-feed", "preview_url": "https://other.example.com/feed.png"
                                                   "?X-Amz-Signature=nope"},
            {"id": "instagram-portrait", "preview_url": url},
        ]
        expected_url = base
    template_id = draw(st.sampled_from(["1bb5c1ad", "tA", "tpl-ñ"]))
    payload: dict = {"template_id": template_id, "elements": expected_elements}
    if expected_url is not None:
        payload["preview_url"] = expected_url
    return template_id, template, payload


@st.composite
def _p32_slots_and_copies(draw):
    from services.adset_diversity import build_variant_slots
    slots = build_variant_slots(P32_PLAN_ID, ad_slot=draw(st.integers(0, 3)),
                                n_variants=draw(st.integers(1, 4)),
                                project_templates=["tA", "tB"])
    subset = draw(st.lists(st.sampled_from(slots), unique_by=lambda s: s["variant_key"],
                           min_size=1, max_size=len(slots)))
    copies = [
        {"plan_id": P32_PLAN_ID, "variant_key": s["variant_key"],
         "template_id": s["template_id"], "headline": ["H"], "primary_text": ["P"],
         "template_elements": [{"element_id": "hook", "text": "H"}]}
        for s in draw(st.lists(st.sampled_from(slots), unique_by=lambda s: s["variant_key"],
                               max_size=len(slots)))
    ]
    if draw(st.booleans()):
        copies.append({"variant_key": "plan_ad_999_v1", "headline": ["foreign"]})
    return subset, copies


# Feature: adset-creative-diversity, Property 32: Línea Image_Elements en el mensaje al Image_Prompter
@settings(max_examples=100, deadline=None)
@given(tpl=_p32_template(), sc=_p32_slots_and_copies())
def test_image_prompt_message_image_elements_line(tpl, sc):
    """**Validates: Requirements 15.4, 15.13, 12.30**"""
    from services.adset_diversity import (
        DEFAULT_DECORATIVE_IMAGE_PATTERNS, build_image_elements, build_image_prompt_message,
    )
    template_id, template, expected_payload = tpl
    slots, copies = sc
    ie = build_image_elements(template_id, template, list(DEFAULT_DECORATIVE_IMAGE_PATTERNS))
    assert list(ie.element_ids) == [e["element_id"] for e in expected_payload["elements"]]
    kwargs = dict(id_adset=7, ad_id=101)

    legacy = build_image_prompt_message(P32_PLAN, slots, copies, P32_CTX_JSON, **kwargs)
    none_msg = build_image_prompt_message(P32_PLAN, slots, copies, P32_CTX_JSON,
                                          image_elements=None, **kwargs)
    msg = build_image_prompt_message(P32_PLAN, slots, copies, P32_CTX_JSON,
                                     image_elements=ie, **kwargs)

    # image_elements=None: byte for byte the message without the kwarg.
    assert none_msg == legacy

    # The with-elements message is the None message plus one block inserted before "Plan: ".
    cut = none_msg.index("\nPlan: ") + 1
    assert msg.startswith(none_msg[:cut]) and msg.endswith(none_msg[cut:])
    added = msg[cut:len(msg) - (len(none_msg) - cut)]
    assert added and msg == none_msg[:cut] + added + none_msg[cut:]

    # Exactly one "Image_Elements: " line, inside the added block, with the expected JSON.
    lines = [ln for ln in msg.split("\n") if ln.startswith("Image_Elements: ")]
    assert len(lines) == 1
    assert lines[0] in added.split("\n")
    assert json.loads(lines[0][len("Image_Elements: "):]) == expected_payload

    # Rules.
    if ie.element_ids:
        assert "EXACTLY one entry per element" in added
        assert "Copy each `element_id` verbatim from Image_Elements" in added
        assert 'set `element_type` to "image"' in added
        assert "NEVER use as element_id an id from the copies' `template_elements`" in added
        assert '"image_prompts": []' not in added
    else:
        assert '"image_prompts": [] in EVERY object' in added
        assert "EXACTLY one entry per element" not in added

    # No signature query string in the text added by P15.
    assert "?" not in added
    for marker in P32_SIGNATURE_MARKERS:
        assert marker not in added


# ---------------------------------------------------------------------------
# Unit tests (task 35.11): extraction, specs and preview URL (Req 15.2, 15.4, 12.29)
# ---------------------------------------------------------------------------
import pytest  # noqa: E402

from services.adset_diversity import (  # noqa: E402
    DEFAULT_DECORATIVE_IMAGE_PATTERNS, build_image_elements, build_image_prompt_message,
    build_variant_slots, check_image_elements, image_element_specs, make_variant_validator,
    template_preview_url,
)
from tests._template_fixtures import (  # noqa: E402
    TEMPLATE_1BB5C1AD, TEMPLATE_1BB5C1AD_ID, template_1bb5c1ad,
)

_DEFAULTS = list(DEFAULT_DECORATIVE_IMAGE_PATTERNS)


def _tpl(*elements) -> dict:
    return {"id": "tpl", "elements": list(elements)}


def test_template_1bb5c1ad_yields_image_0():
    """**Validates: Requirements 15.2, 12.29**"""
    template = template_1bb5c1ad()
    assert template_image_elements(template, _DEFAULTS) == ["image_0"]
    assert template == TEMPLATE_1BB5C1AD  # not mutated


def test_id_used_when_name_missing_and_empty_ids_skipped():
    """**Validates: Requirements 15.2, 12.29**"""
    template = _tpl(
        {"type": "image", "id": "photo_a"},
        {"type": "image", "name": "", "id": "photo_b"},
        {"type": "image"},
        {"type": "image", "name": None, "id": ""},
        {"type": "image", "name": "photo_c", "id": "ignored"},
    )
    assert template_image_elements(template, _DEFAULTS) == ["photo_a", "photo_b", "photo_c"]


def test_repeated_ids_kept_once_at_first_position():
    """**Validates: Requirements 15.2, 12.29**"""
    template = _tpl(
        {"type": "image", "name": "b"}, {"type": "image", "name": "a"},
        {"type": "image", "name": "b"}, {"type": "image", "id": "a"},
    )
    assert template_image_elements(template, _DEFAULTS) == ["b", "a"]


def test_patterns_case_insensitive_and_empty_setting_excludes_nothing():
    """**Validates: Requirements 15.2, 15.12, 12.29**"""
    template = _tpl(
        {"type": "image", "name": "Gradient_Top"}, {"type": "image", "name": "OVERLAY_1"},
        {"type": "image", "name": "image_0"},
    )
    assert template_image_elements(template, _DEFAULTS) == ["image_0"]
    assert template_image_elements(template, []) == ["Gradient_Top", "OVERLAY_1", "image_0"]
    # Empty or whitespace-only patterns are ignored (they would match everything).
    assert template_image_elements(template, ["", "   ", "\t"]) == [
        "Gradient_Top", "OVERLAY_1", "image_0"]
    assert template_image_elements(template, [" ", " overlay "]) == ["Gradient_Top", "image_0"]


def test_type_must_be_exactly_image_and_no_images_gives_empty():
    """**Validates: Requirements 15.2, 12.29**"""
    template = _tpl(
        {"type": "Image", "name": "a"}, {"type": "IMAGE", "name": "b"},
        {"name": "c"}, {"type": "text", "name": "hook"}, {"type": "logo", "name": "logo_0"},
        "not-a-dict", None,
    )
    assert template_image_elements(template, _DEFAULTS) == []
    assert template_image_elements(_tpl(), _DEFAULTS) == []


def test_image_element_specs_with_and_without_layout():
    """**Validates: Requirements 15.4**"""
    template = template_1bb5c1ad()
    template["elements"].append({"type": "image", "name": "bare"})
    template["elements"].append(
        {"type": "image", "name": "other_fmt", "layout": {"facebook-feed": {"width": 5,
                                                                           "height": 5}}})
    specs = image_element_specs(template, ["image_0", "bare", "other_fmt"])
    assert specs == [
        {"element_id": "image_0", "width": 1080, "height": 1350},
        {"element_id": "bare"},
        {"element_id": "other_fmt"},
    ]


def test_template_preview_url_top_level_formats_and_query_string():
    """**Validates: Requirements 15.4, 15.13**"""
    # Top level wins and drops the query string.
    assert template_preview_url({
        "preview_url": "https://cdn.example.com/p.png?X-Amz-Signature=abc&Expires=1",
        "formats": [{"id": "instagram-portrait", "preview_url": "https://other/x.png"}],
    }) == "https://cdn.example.com/p.png"
    # From formats (instagram-portrait entry), as in the 1bb5c1ad fixture.
    assert template_preview_url(TEMPLATE_1BB5C1AD) == (
        "https://production-banners.s3-eu-west-1.amazonaws.com/templates/"
        f"{TEMPLATE_1BB5C1AD_ID}/preview-instagram-portrait.png")
    assert template_preview_url({"formats": [
        {"id": "facebook-feed", "preview_url": "https://feed/x.png"},
        {"id": "instagram-portrait", "preview_url": "https://ig/x.png?Signature=s&Key-Pair-Id=k"},
    ]}) == "https://ig/x.png"
    assert template_preview_url({"preview_url": ""}) is None
    assert template_preview_url({"elements": []}) is None


# ---------------------------------------------------------------------------
# Unit tests: message to the Image_Prompter (Req 15.4, 15.13, 12.30)
# ---------------------------------------------------------------------------

def _msg_slots():
    return build_variant_slots(P32_PLAN_ID, ad_slot=0, n_variants=2,
                               project_templates=["tA", "tB"])


def _image_elements_lines(msg: str) -> list[str]:
    return [ln for ln in msg.split("\n") if ln.startswith("Image_Elements: ")]


def test_message_line_with_template_id_and_ordered_ids_and_rules():
    """**Validates: Requirements 15.4, 12.30**"""
    template = _tpl(
        {"type": "image", "name": "photo_b",
         "layout": {"instagram-portrait": {"width": 600, "height": 400}}},
        {"type": "text", "name": "hook"},
        {"type": "image", "name": "photo_a"},
        {"type": "image", "name": "degradado_top"},
    )
    ie = build_image_elements("1bb5c1ad", template, _DEFAULTS)
    slots = _msg_slots()
    msg = build_image_prompt_message(P32_PLAN, slots, [], P32_CTX_JSON, id_adset=7,
                                     ad_id=101, image_elements=ie)
    lines = _image_elements_lines(msg)
    assert len(lines) == 1
    payload = json.loads(lines[0][len("Image_Elements: "):])
    assert payload == {"template_id": "1bb5c1ad", "elements": [
        {"element_id": "photo_b", "width": 600, "height": 400}, {"element_id": "photo_a"}]}
    assert "EXACTLY one entry per element" in msg
    assert "Copy each `element_id` verbatim from Image_Elements" in msg
    assert 'set `element_type` to "image"' in msg
    assert "NEVER use as element_id an id from the copies' `template_elements`" in msg
    assert '"image_prompts": []' not in msg


def test_message_empty_image_elements_requires_empty_list():
    """**Validates: Requirements 15.4, 12.30**"""
    ie = build_image_elements("tA", _tpl({"type": "text", "name": "hook"}), _DEFAULTS)
    assert ie.element_ids == ()
    msg = build_image_prompt_message(P32_PLAN, _msg_slots(), [], P32_CTX_JSON, id_adset=7,
                                     ad_id=101, image_elements=ie)
    lines = _image_elements_lines(msg)
    assert len(lines) == 1
    assert json.loads(lines[0][len("Image_Elements: "):]) == {"template_id": "tA",
                                                               "elements": []}
    assert '"image_prompts": [] in EVERY object' in msg
    assert "EXACTLY one entry per element" not in msg


def test_message_contains_no_signed_url():
    """**Validates: Requirements 15.4, 15.13, 12.30**"""
    template = template_1bb5c1ad()
    template["preview_url"] = ("https://bucket.s3.amazonaws.com/p.png?X-Amz-Algorithm=AWS4"
                               "&X-Amz-Credential=AKIA&X-Amz-Signature=deadbeef&Expires=60")
    ie = build_image_elements(TEMPLATE_1BB5C1AD_ID, template, _DEFAULTS)
    msg = build_image_prompt_message(P32_PLAN, _msg_slots(), [], P32_CTX_JSON, id_adset=7,
                                     ad_id=101, image_elements=ie)
    payload = json.loads(_image_elements_lines(msg)[0][len("Image_Elements: "):])
    assert payload["preview_url"] == "https://bucket.s3.amazonaws.com/p.png"
    assert payload["elements"] == [{"element_id": "image_0", "width": 1080, "height": 1350}]
    for marker in ("X-Amz-", "Signature", "Expires", "AKIA", "deadbeef"):
        assert marker not in msg


def test_message_with_none_equals_current_message():
    """**Validates: Requirements 15.4, 12.30**"""
    slots = _msg_slots()
    legacy = build_image_prompt_message(P32_PLAN, slots, [], P32_CTX_JSON, id_adset=7,
                                        ad_id=101)
    assert build_image_prompt_message(P32_PLAN, slots, [], P32_CTX_JSON, id_adset=7,
                                      ad_id=101, image_elements=None) == legacy
    assert "Image_Elements" not in legacy


# ---------------------------------------------------------------------------
# Unit tests: Image_Elements_Checker and composite validator (Req 15.5, 15.6, 15.7, 12.31)
# ---------------------------------------------------------------------------
UT_PLAN_ID = "plan_ad_102"


def _ut_slots(n=1):
    return build_variant_slots(UT_PLAN_ID, ad_slot=0, n_variants=n,
                               project_templates=[TEMPLATE_1BB5C1AD_ID])


def _ut_item(slot, prompts) -> dict:
    return {"plan_id": UT_PLAN_ID, "variant_key": slot["variant_key"],
            "template_id": slot["template_id"], "image_prompts": prompts}


def _p(eid, etype="image") -> dict:
    return {"element_id": eid, "element_type": etype, "prompt": f"photo for {eid}"}


def _ut_validator(slots, image_elements):
    from services.ads_validators import validate_image_prompter_response
    return make_variant_validator(validate_image_prompter_response, slots, UT_PLAN_ID,
                                  kind="image_prompt", image_elements=image_elements)


def test_ad_102_job_69d025e1_text_layers_rejected():
    """**Validates: Requirements 15.5, 15.6, 12.31**"""
    slots = _ut_slots()
    key = slots[0]["variant_key"]
    response = json.dumps([_ut_item(slots[0], [_p("hook"), _p("tagline")])])
    result = _ut_validator(slots, ["image_0"])(response)
    assert not result.is_valid
    assert result.error_code == "ERR_VARIANT_SHAPE"
    assert result.data is None
    assert len(result.errors) == 1
    err = result.errors[0]
    for fragment in (key, "image_0", "hook", "tagline"):
        assert fragment in err


@pytest.mark.parametrize("prompts", [
    pytest.param([_p("image_0")], id="missing"),
    pytest.param([_p("image_0"), _p("image_1"), _p("extra")], id="extra"),
    pytest.param([_p("image_0"), _p("image_1"), _p("image_0")], id="repeated"),
    pytest.param([_p("image_0"), _p("image_1", "text")], id="element_type"),
    pytest.param([_p("image_0"), {"element_id": "image_1", "prompt": "x"}],
                 id="element_type_missing"),
])
def test_checker_and_validator_reject_bad_sets(prompts):
    """**Validates: Requirements 15.5, 15.6, 12.31**"""
    slots = _ut_slots()
    item = _ut_item(slots[0], prompts)
    errors = check_image_elements([item], ["image_0", "image_1"])
    assert len(errors) == 1 and slots[0]["variant_key"] in errors[0]
    result = _ut_validator(slots, ["image_0", "image_1"])(json.dumps([item]))
    assert not result.is_valid and result.error_code == "ERR_VARIANT_SHAPE"
    assert result.errors == errors


def test_exact_set_in_other_order_accepted():
    """**Validates: Requirements 15.5, 15.6, 12.31**"""
    slots = _ut_slots(2)
    items = [_ut_item(slots[0], [_p("image_1"), _p("image_0")]),
             _ut_item(slots[1], [_p("image_0"), _p("image_1")])]
    assert check_image_elements(items, ["image_0", "image_1"]) == []
    result = _ut_validator(slots, ["image_0", "image_1"])(json.dumps(items))
    assert result.is_valid, result.errors
    assert [[el["element_id"] for el in it["image_prompts"]] for it in result.data] == [
        ["image_1", "image_0"], ["image_0", "image_1"]]


def test_empty_image_prompts_accepted_with_empty_image_elements():
    """**Validates: Requirements 15.5, 15.6, 12.31**"""
    slots = _ut_slots()
    item = _ut_item(slots[0], [])
    assert check_image_elements([item], []) == []
    assert _ut_validator(slots, [])(json.dumps([item])).is_valid
    # With empty Image_Elements any entry is rejected.
    assert len(check_image_elements([_ut_item(slots[0], [_p("image_0")])], [])) == 1


def test_copy_kind_with_image_elements_raises():
    """**Validates: Requirements 15.7**"""
    from services.ads_validators import validate_copywriter_response
    with pytest.raises(ValueError):
        make_variant_validator(validate_copywriter_response, _ut_slots(), UT_PLAN_ID,
                               kind="copy", image_elements=["image_0"])


def test_variant_shape_is_retryable():
    """**Validates: Requirements 15.6, 12.31**"""
    import services.job_runner_service as jrs
    assert "ERR_VARIANT_SHAPE" in jrs._RETRYABLE_AGENT_CODES


# ---------------------------------------------------------------------------
# Unit tests: setting, env.example and OUTPUT_CONTRACT_SECTION (Req 15.12, 15.14)
# ---------------------------------------------------------------------------

def test_decorative_patterns_setting_default_and_env_example():
    """**Validates: Requirements 15.12**"""
    from pathlib import Path

    from core.config import Settings
    expected = ["degradado", "gradient", "overlay", "mask", "shape"]
    assert Settings.model_fields["ADSET_DECORATIVE_IMAGE_PATTERNS"].default == expected
    assert list(DEFAULT_DECORATIVE_IMAGE_PATTERNS) == expected
    env_example = (Path(__file__).resolve().parents[1] / "env.example").read_text("utf-8")
    lines = env_example.splitlines()
    matches = [i for i, ln in enumerate(lines)
               if ln.startswith("ADSET_DECORATIVE_IMAGE_PATTERNS=")]
    assert len(matches) == 1
    value = lines[matches[0]].split("=", 1)[1]
    assert json.loads(value) == expected
    # Documented with a comment right above (decorative, case-insensitive).
    comment = []
    for ln in reversed(lines[:matches[0]]):
        if not ln.startswith("#"):
            break
        comment.append(ln)
    text = " ".join(comment).lower()
    assert comment and "decorativ" in text and "mayúsculas" in text


def test_output_contract_rule_only_in_variant_mode():
    """**Validates: Requirements 15.14**"""
    from agents.image_prompter_agent import OUTPUT_CONTRACT_SECTION
    section = OUTPUT_CONTRACT_SECTION
    start = section.index("2. VARIANT MODE")
    end = section.index('Without a "Variant_Slots:" line')
    assert section.count("Image_Elements:") == 1
    pos = section.index("Image_Elements:")
    assert start < pos < end
    variant_mode = section[start:end]
    assert "source of truth" in variant_mode
    assert "Image_Elements" not in section[:start] + section[end:]


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
