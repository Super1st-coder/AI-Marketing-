"""Property-based tests for the ad_variant_image_prompter validator and the
`image_prompt` extraction used by the edit pipeline.

Run:  PYTHONPATH=. env/bin/python -m pytest tests/test_ad_variant_image_prompter_validator_properties.py
  or: PYTHONPATH=. env/bin/python -m tests.test_ad_variant_image_prompter_validator_properties
"""
from __future__ import annotations

import json
from typing import Any

from hypothesis import given, settings, strategies as st

from services.ads_validators import validate_ad_variant_image_prompter_response
from services.job_runner_service import _extract_image_prompt

MAX_CHARS = 2000

# ---------------------------------------------------------------------------
# Oracle (independent of the implementation)
# ---------------------------------------------------------------------------


def _expected_valid(obj: Any) -> bool:
    """A parsed JSON value is acceptable iff it is an object whose `image_prompt`
    is a str with 1..2000 characters after strip."""
    if not isinstance(obj, dict) or "image_prompt" not in obj:
        return False
    prompt = obj["image_prompt"]
    return isinstance(prompt, str) and 1 <= len(prompt.strip()) <= MAX_CHARS


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

_ws = st.text(alphabet=" \t\n\r", max_size=4)
_char = st.characters(blacklist_categories=("Cs",))
_json_scalar = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(_char, max_size=10),
)
_json_value = st.recursive(
    _json_scalar,
    lambda children: st.one_of(
        st.lists(children, max_size=3),
        st.dictionaries(st.text(_char, max_size=5), children, max_size=3),
    ),
    max_leaves=6,
)


@st.composite
def _prompt_strings(draw) -> str:
    """Strings around the [1, 2000] window (incl. blank) with optional padding."""
    n = draw(st.one_of(st.integers(0, 2100), st.sampled_from([0, 1, 1999, 2000, 2001])))
    alphabet = draw(st.sampled_from(["a", "ab c", " \t\n", "xyzñ€😀 "]))
    core = draw(st.text(alphabet=alphabet, min_size=n, max_size=n))
    return draw(_ws) + core + draw(_ws)


@st.composite
def _json_candidates(draw) -> Any:
    """JSON values: non-objects, objects without `image_prompt`, objects whose
    `image_prompt` is any JSON type or a str of length 0..2100 (blank included)."""
    kind = draw(st.sampled_from(["non_object", "missing", "any_type", "string"]))
    if kind == "non_object":
        return draw(_json_value.filter(lambda v: not isinstance(v, dict)))
    extra = draw(
        st.dictionaries(
            st.text(_char, max_size=6).filter(lambda k: k != "image_prompt"),
            _json_scalar,
            max_size=3,
        )
    )
    if kind == "missing":
        return extra
    prompt = draw(_json_value) if kind == "any_type" else draw(_prompt_strings())
    return {**extra, "image_prompt": prompt}


def _encode(draw, obj: Any) -> str:
    """Serialize as JSON text, optionally wrapped in a ```json fence and padded."""
    text = json.dumps(obj, ensure_ascii=draw(st.booleans()))
    fence = draw(st.sampled_from([None, "```json\n", "```\n", "```JSON "]))
    if fence is not None:
        text = f"{fence}{text}\n```"
    return draw(_ws) + text + draw(_ws)


@st.composite
def _encoded_candidates(draw) -> tuple[str, Any]:
    obj = draw(_json_candidates())
    return _encode(draw, obj), obj


@st.composite
def _valid_prompts(draw) -> tuple[str, dict[str, Any]]:
    prompt = draw(_prompt_strings().filter(lambda p: 1 <= len(p.strip()) <= MAX_CHARS))
    extra = draw(
        st.dictionaries(
            st.text(_char, max_size=6).filter(lambda k: k != "image_prompt"),
            _json_scalar,
            max_size=2,
        )
    )
    obj = {**extra, "image_prompt": prompt}
    return _encode(draw, obj), obj


# ---------------------------------------------------------------------------
# Property 14
# ---------------------------------------------------------------------------


def _check_validator(s: str, expected: bool, obj: Any = None) -> None:
    result = validate_ad_variant_image_prompter_response(s)
    assert result.is_valid is expected, (s[:200], result.error_code, result.errors)
    if expected:
        assert result.data["image_prompt"] == obj["image_prompt"].strip()
        assert result.errors == []
    else:
        assert result.errors, (s[:200], result.error_code)


# Feature: ad-variant-image-edit-pipeline, Property 14: Oráculo del Prompter_Validator y de la extracción
@settings(max_examples=100, deadline=None)
@given(case=_encoded_candidates())
def test_property_14_validator_oracle_on_json_inputs(case: tuple[str, Any]) -> None:
    """**Validates: Requirements 8.5, 8.6, 13.17**"""
    s, obj = case
    _check_validator(s, _expected_valid(obj), obj)


# Feature: ad-variant-image-edit-pipeline, Property 14: Oráculo del Prompter_Validator y de la extracción
@settings(max_examples=100, deadline=None)
@given(s=st.text(_char, max_size=200))
def test_property_14_validator_oracle_on_arbitrary_text(s: str) -> None:
    """**Validates: Requirements 8.5, 8.6, 13.17**"""
    try:
        obj = json.loads(s.strip())
        expected = _expected_valid(obj)
    except ValueError:
        obj, expected = None, False
    _check_validator(s, expected, obj)


# Feature: ad-variant-image-edit-pipeline, Property 14: Oráculo del Prompter_Validator y de la extracción
@settings(max_examples=100, deadline=None)
@given(case=_valid_prompts())
def test_property_14_extract_same_for_text_and_dict(case: tuple[str, dict[str, Any]]) -> None:
    """**Validates: Requirements 8.8**"""
    s, obj = case
    expected = obj["image_prompt"].strip()
    from_text = _extract_image_prompt(s)
    from_dict = _extract_image_prompt(json.loads(json.dumps(obj)))
    assert from_text == expected
    assert from_dict == expected
    # The validator's `data` (what run_agent hands back) extracts to the same value.
    data = validate_ad_variant_image_prompter_response(s).data
    assert _extract_image_prompt(data) == expected


# Feature: ad-variant-image-edit-pipeline, Property 14: Oráculo del Prompter_Validator y de la extracción
@settings(max_examples=100, deadline=None)
@given(obj=_json_candidates().filter(lambda v: isinstance(v, dict)))
def test_property_14_extract_dict_matches_oracle(obj: dict[str, Any]) -> None:
    """**Validates: Requirements 8.8**"""
    expected = obj["image_prompt"].strip() if _expected_valid(obj) else None
    assert _extract_image_prompt(obj) == expected


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ad-variant-image-prompter validator property tests passed")
