"""Property-based tests for the ad-variant image edit schemas.

Run:  PYTHONPATH=. env/bin/python -m pytest tests/test_ad_variant_image_edit_schemas_properties.py
  or: PYTHONPATH=. env/bin/python -m tests.test_ad_variant_image_edit_schemas_properties
"""
from __future__ import annotations

from typing import Any

from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from schemas.pipeline_schemas import AdVariantImageEditCreate

_ABSENT = object()  # sentinel: key not present in the payload

_ID_FIELDS = ("brand_id", "campaign_id", "ad_id", "channel_id", "variant_id")
_STR_FIELDS = ("image_name", "id_base_image")
_ZOOM_VALUES = ("TOP", "BOTTOM", "LEFT", "RIGHT", "ZOOM_2X", "ZOOM_1_5X", "ZOOM_1_25X")
_EITHER_OR_MSG = "custom_prompt, expand_zoom_option o ambos"

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

_whitespace = st.text(alphabet=" \t\n\r", min_size=0, max_size=4)
_blank = st.text(alphabet=" \t\n\r", min_size=1, max_size=6)
_core_char = st.characters(blacklist_categories=("Cs", "Zs", "Zl", "Zp", "Cc"))


def _padded(min_len: int, max_len: int) -> st.SearchStrategy[str]:
    """Non-blank core of length in [min_len, max_len] with optional whitespace padding."""
    return st.tuples(
        _whitespace, st.text(_core_char, min_size=min_len, max_size=max_len), _whitespace
    ).map(lambda t: t[0] + t[1] + t[2])


def _int_like(min_value: int, max_value: int) -> st.SearchStrategy[Any]:
    """Values convertible to int in lax mode (int, numeric str, integral float)."""
    ints = st.integers(min_value=min_value, max_value=max_value)
    return st.one_of(ints, ints.map(str), ints.map(float))


_not_int = st.one_of(
    st.none(),
    st.sampled_from(["abc", "", "1.5", "x1", "   "]),
    st.floats(allow_nan=False, allow_infinity=False).filter(lambda f: not f.is_integer()),
    st.lists(st.integers(), max_size=2),
    st.dictionaries(st.text(max_size=3), st.integers(), max_size=1),
)

_id_value = st.one_of(_int_like(1, 10**9), _int_like(-5, 0), _not_int, st.just(_ABSENT))
_n_variations = st.one_of(_int_like(1, 10), _int_like(-3, 0), _int_like(11, 50), _not_int, st.just(_ABSENT))

_required_str = st.one_of(
    _padded(1, 20),
    _padded(250, 260),          # boundary around 255/256 after stripping
    _blank,                     # whitespace-only → "" after stripping
    st.just(""),
    st.none(),
    st.integers(),              # not convertible to str
    st.just(_ABSENT),
)

_custom_prompt = st.one_of(
    _padded(1, 30),
    _padded(1995, 2005),        # boundary around 2000/2001 after stripping
    _blank,
    st.just(""),
    st.none(),
    st.integers(),
    st.just(_ABSENT),
)

_expand_zoom_option = st.one_of(
    st.sampled_from(_ZOOM_VALUES),
    st.sampled_from(_ZOOM_VALUES).map(str.lower),
    st.sampled_from(["ZOOM_3X", "zoom", "", " TOP", "Top"]),
    st.text(max_size=10),
    st.integers(),
    st.none(),
    st.just(_ABSENT),
)


# "Likely valid" strategies (boundary lengths may still be invalid), so that a
# good share of generated payloads is fully valid and both sides of the
# iff are exercised.
_LIKELY_VALID: dict[str, st.SearchStrategy[Any]] = {
    **{f: _int_like(1, 10**9) for f in _ID_FIELDS},
    **{f: st.one_of(_padded(1, 20), _padded(250, 260)) for f in _STR_FIELDS},
    "n_variations": _int_like(1, 10),
    "custom_prompt": st.one_of(_padded(1, 30), _padded(1995, 2005), _blank, st.none(), st.just(_ABSENT)),
    "expand_zoom_option": st.one_of(st.sampled_from(_ZOOM_VALUES), st.none(), st.just(_ABSENT)),
}
_ANY: dict[str, st.SearchStrategy[Any]] = {
    **{f: _id_value for f in _ID_FIELDS},
    **{f: _required_str for f in _STR_FIELDS},
    "n_variations": _n_variations,
    "custom_prompt": _custom_prompt,
    "expand_zoom_option": _expand_zoom_option,
}


@st.composite
def _payloads(draw) -> dict[str, Any]:
    # Pick a (possibly empty) subset of fields drawn from the full, mostly-invalid space.
    wild = draw(st.sets(st.sampled_from(sorted(_ANY)), max_size=3))
    raw = {f: draw(_ANY[f] if f in wild else _LIKELY_VALID[f]) for f in _ANY}
    return {k: v for k, v in raw.items() if v is not _ABSENT}


# ---------------------------------------------------------------------------
# Reference predicate (independent of the schema implementation)
# ---------------------------------------------------------------------------

def _as_int(v: Any) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else None
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return None
    return None


def _expected(payload: dict[str, Any]) -> tuple[set[str], bool]:
    """Return (field culprits, either-or rule violated)."""
    culprits: set[str] = set()

    for f in _ID_FIELDS:
        n = _as_int(payload[f]) if f in payload else None
        if n is None or n < 1:
            culprits.add(f)

    n = _as_int(payload["n_variations"]) if "n_variations" in payload else None
    if n is None or not 1 <= n <= 10:
        culprits.add("n_variations")

    for f in _STR_FIELDS:
        v = payload.get(f)
        if not isinstance(v, str) or not 1 <= len(v.strip()) <= 255:
            culprits.add(f)

    prompt = payload.get("custom_prompt")
    prompt_present = False
    if prompt is not None:
        if not isinstance(prompt, str) or len(prompt.strip()) > 2000:
            culprits.add("custom_prompt")
        else:
            prompt_present = bool(prompt.strip())

    zoom = payload.get("expand_zoom_option")
    if zoom is not None and zoom not in _ZOOM_VALUES:
        culprits.add("expand_zoom_option")

    either_or_violated = not prompt_present and zoom is None
    return culprits, either_or_violated


# ---------------------------------------------------------------------------
# Property 1
# ---------------------------------------------------------------------------

# Feature: ad-variant-image-edit-pipeline, Property 1: El schema acepta exactamente los payloads válidos
@settings(max_examples=100, deadline=None)
@given(payload=_payloads())
def test_property_1_schema_accepts_exactly_valid_payloads(payload: dict[str, Any]) -> None:
    """**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.10, 1.11, 13.14**"""
    culprits, either_or_violated = _expected(payload)
    should_pass = not culprits and not either_or_violated

    try:
        AdVariantImageEditCreate.model_validate(payload)
    except ValidationError as exc:
        assert not should_pass, f"valid payload rejected: {exc}"
        errors = exc.errors()
        if culprits:
            # Field validation fails first; every culprit (and only those) appears in loc.
            assert {e["loc"][0] for e in errors if e["loc"]} == culprits, errors
        else:
            # Only the model-level either-or rule fails (FastAPI reports it as loc=["body"]).
            assert len(errors) == 1 and errors[0]["loc"] == (), errors
            assert _EITHER_OR_MSG in errors[0]["msg"], errors
        return

    assert should_pass, f"invalid payload accepted (culprits={culprits}, either_or={either_or_violated})"


# ---------------------------------------------------------------------------
# Property 2
# ---------------------------------------------------------------------------
@st.composite
def _valid_payloads(draw) -> dict[str, Any]:
    """Payloads that are always valid; strings carry optional whitespace padding."""
    payload: dict[str, Any] = {f: draw(_int_like(1, 10**9)) for f in _ID_FIELDS}
    payload["n_variations"] = draw(_int_like(1, 10))
    for f in _STR_FIELDS:
        payload[f] = draw(st.one_of(_padded(1, 20), _padded(250, 255)))
    prompt = draw(st.one_of(_padded(1, 30), _padded(1995, 2000), _blank, st.just(""), st.none(), st.just(_ABSENT)))
    prompt_present = isinstance(prompt, str) and bool(prompt.strip())
    zoom_choices = st.sampled_from(_ZOOM_VALUES)
    if prompt_present:
        zoom_choices = st.one_of(zoom_choices, st.none(), st.just(_ABSENT))
    zoom = draw(zoom_choices)
    payload["custom_prompt"] = prompt
    payload["expand_zoom_option"] = zoom
    return {k: v for k, v in payload.items() if v is not _ABSENT}


# Feature: ad-variant-image-edit-pipeline, Property 2: Normalización de cadenas idempotente
@settings(max_examples=100, deadline=None)
@given(payload=_valid_payloads())
def test_property_2_string_normalization_idempotent(payload: dict[str, Any]) -> None:
    """**Validates: Requirements 1.12**"""
    model = AdVariantImageEditCreate.model_validate(payload)
    assert model.image_name == payload["image_name"].strip()
    assert model.id_base_image == payload["id_base_image"].strip()
    raw_prompt = payload.get("custom_prompt")
    expected_prompt = (raw_prompt.strip() or None) if isinstance(raw_prompt, str) else None
    assert model.custom_prompt == expected_prompt
    # Re-validating the JSON dump yields an equal model (idempotence).
    again = AdVariantImageEditCreate.model_validate(model.model_dump(mode="json"))
    assert again == model
    assert again.model_dump(mode="json") == model.model_dump(mode="json")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ad-variant-image-edit schema property tests passed")
