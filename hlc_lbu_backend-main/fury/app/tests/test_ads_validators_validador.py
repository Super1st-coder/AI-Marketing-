"""Tests for `validate_validador_response` (Requirement 7.11).

Run:  PYTHONPATH=. env/bin/python -m pytest tests/test_ads_validators_validador.py
  or: PYTHONPATH=. env/bin/python -m tests.test_ads_validators_validador
"""
from __future__ import annotations

import json

from hypothesis import given, settings, strategies as st

from services.ads_validators import validate_validador_response

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_MISSING = object()

# Any JSON value (scalars, lists, objects), including booleans.
_json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=20),
    lambda children: st.lists(children, max_size=4)
    | st.dictionaries(st.text(max_size=8), children, max_size=4),
    max_leaves=10,
)

# Field value: absent, or any JSON type (booleans/lists boosted so the
# valid branch is exercised often).
_overall_pass = st.one_of(st.just(_MISSING), st.booleans(), _json_values)
_subset = st.one_of(
    st.just(_MISSING), st.lists(_json_values, max_size=4), _json_values
)

# Extra unrelated keys the Validador may return.
_extra = st.dictionaries(
    st.text(max_size=8).filter(
        lambda k: k not in ("overall_pass", "subset_to_regenerate")
    ),
    _json_values,
    max_size=3,
)


# ---------------------------------------------------------------------------
# Property 15
# ---------------------------------------------------------------------------

# Feature: adset-creative-diversity, Property 15: validate_validador_response acepta overall_pass=False
@settings(max_examples=100, deadline=None)
@given(overall_pass=_overall_pass, subset=_subset, extra=_extra)
def test_property_15_validador_response_accepts_overall_pass_false(
    overall_pass, subset, extra
):
    """**Validates: Requirements 7.11**

    For any JSON object with `overall_pass` absent or of any JSON type and
    `subset_to_regenerate` absent or of any JSON type, the response is valid
    iff `overall_pass` is a bool (True or False) and `subset_to_regenerate`
    is a list; the validator never raises.
    """
    obj = dict(extra)
    if overall_pass is not _MISSING:
        obj["overall_pass"] = overall_pass
    if subset is not _MISSING:
        obj["subset_to_regenerate"] = subset

    expected = isinstance(obj.get("overall_pass"), bool) and isinstance(
        obj.get("subset_to_regenerate"), list
    )

    result = validate_validador_response(json.dumps(obj))  # must not raise

    assert result.is_valid is expected, (obj, result.errors)
    if expected:
        assert result.data == obj
        assert result.errors == []
    else:
        assert result.errors


# ---------------------------------------------------------------------------
# Unit tests (Requirements 7.11, 12.18)
# ---------------------------------------------------------------------------


def test_overall_pass_false_with_list_is_accepted():
    obj = {"overall_pass": False, "subset_to_regenerate": [{"index": 0}]}
    result = validate_validador_response(json.dumps(obj))
    assert result.is_valid, result.errors
    assert result.data == obj
    assert result.errors == []


def test_overall_pass_true_with_empty_list_is_accepted():
    obj = {"overall_pass": True, "subset_to_regenerate": []}
    result = validate_validador_response(json.dumps(obj))
    assert result.is_valid, result.errors
    assert result.data == obj


def test_overall_pass_missing_is_rejected():
    result = validate_validador_response(json.dumps({"subset_to_regenerate": []}))
    assert not result.is_valid
    assert result.errors


def test_overall_pass_not_boolean_is_rejected():
    for value in ("false", 0, 1, None, [], {}):
        obj = {"overall_pass": value, "subset_to_regenerate": []}
        result = validate_validador_response(json.dumps(obj))
        assert not result.is_valid, obj
        assert result.errors, obj


def test_subset_to_regenerate_missing_is_rejected():
    result = validate_validador_response(json.dumps({"overall_pass": False}))
    assert not result.is_valid
    assert result.errors


def test_subset_to_regenerate_not_list_is_rejected():
    for value in (None, "[]", 0, {}, True):
        obj = {"overall_pass": False, "subset_to_regenerate": value}
        result = validate_validador_response(json.dumps(obj))
        assert not result.is_valid, obj
        assert result.errors, obj


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all validador response tests passed")
