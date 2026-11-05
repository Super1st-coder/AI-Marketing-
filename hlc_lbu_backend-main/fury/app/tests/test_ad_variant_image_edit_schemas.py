"""Unit tests for the ad-variant image edit payload schemas (Req 1.1–1.12).

Covers ExpandZoomOption membership and concrete valid/invalid
AdVariantImageEditCreate payloads, asserting the offending field's ``loc``.

Runnable two ways:
    python -m tests.test_ad_variant_image_edit_schemas   # plain asserts
    pytest tests/test_ad_variant_image_edit_schemas.py   # standard collection
"""
from __future__ import annotations

from enum import Enum

from pydantic import ValidationError

from schemas.pipeline_schemas import AdVariantImageEditCreate, ExpandZoomOption

_EXPECTED_MEMBERS = ["TOP", "BOTTOM", "LEFT", "RIGHT", "ZOOM_2X", "ZOOM_1_5X", "ZOOM_1_25X"]
_REQUIRED = [
    "brand_id", "campaign_id", "ad_id", "channel_id", "variant_id",
    "image_name", "id_base_image", "n_variations",
]
_INT_FIELDS = ["brand_id", "campaign_id", "ad_id", "channel_id", "variant_id", "n_variations"]
_ID_FIELDS = ["brand_id", "campaign_id", "ad_id", "channel_id", "variant_id"]


def _payload(**overrides):
    base = {
        "brand_id": 1,
        "campaign_id": 2,
        "ad_id": 3,
        "channel_id": 4,
        "variant_id": 5,
        "image_name": "hero",
        "id_base_image": "img-123",
        "n_variations": 3,
        "custom_prompt": "make the sky purple",
        "expand_zoom_option": None,
    }
    base.update(overrides)
    return base


def _error_locs(payload) -> list[tuple]:
    """Validate and return the list of error ``loc`` tuples (fails if valid)."""
    try:
        AdVariantImageEditCreate.model_validate(payload)
    except ValidationError as exc:
        return [tuple(e["loc"]) for e in exc.errors()]
    raise AssertionError(f"payload unexpectedly valid: {payload!r}")


def _assert_rejected_on(payload, field: str) -> None:
    locs = _error_locs(payload)
    assert any(loc and loc[0] == field for loc in locs), f"{field} not in {locs}"


# ── ExpandZoomOption (Req 1.8, 1.5) ─────────────────────────────────────────

def test_expand_zoom_option_has_exactly_seven_members_value_equals_name():
    assert issubclass(ExpandZoomOption, str)
    assert issubclass(ExpandZoomOption, Enum)
    assert [m.name for m in ExpandZoomOption] == _EXPECTED_MEMBERS
    assert len(ExpandZoomOption) == 7
    for member in ExpandZoomOption:
        assert member.value == member.name


def test_expand_zoom_option_every_member_accepted_in_payload():
    for name in _EXPECTED_MEMBERS:
        req = AdVariantImageEditCreate.model_validate(
            _payload(custom_prompt=None, expand_zoom_option=name)
        )
        assert req.expand_zoom_option is ExpandZoomOption[name]


def test_expand_zoom_option_rejects_lowercase_and_unknown():
    for bad in ("top", "ZOOM_3X"):
        _assert_rejected_on(_payload(expand_zoom_option=bad), "expand_zoom_option")


# ── Valid payloads (Req 1.1, 1.2, 1.12) ─────────────────────────────────────

def test_valid_payload_with_custom_prompt_only():
    req = AdVariantImageEditCreate.model_validate(_payload())
    assert req.custom_prompt == "make the sky purple"
    assert req.expand_zoom_option is None


def test_valid_payload_with_option_only_and_defaults_none():
    payload = _payload(expand_zoom_option="ZOOM_2X")
    del payload["custom_prompt"]
    req = AdVariantImageEditCreate.model_validate(payload)
    assert req.custom_prompt is None
    assert req.expand_zoom_option is ExpandZoomOption.ZOOM_2X


def test_valid_payload_with_both():
    req = AdVariantImageEditCreate.model_validate(_payload(expand_zoom_option="LEFT"))
    assert req.custom_prompt == "make the sky purple"
    assert req.expand_zoom_option is ExpandZoomOption.LEFT


def test_n_variations_bounds_accepted():
    for n in (1, 10):
        assert AdVariantImageEditCreate.model_validate(_payload(n_variations=n)).n_variations == n


def test_strings_are_stripped_and_blank_prompt_normalized():
    req = AdVariantImageEditCreate.model_validate(
        _payload(image_name="  hero  ", id_base_image=" img-1 ", custom_prompt="  hi  ")
    )
    assert req.image_name == "hero"
    assert req.id_base_image == "img-1"
    assert req.custom_prompt == "hi"

    req = AdVariantImageEditCreate.model_validate(
        _payload(custom_prompt="   ", expand_zoom_option="TOP")
    )
    assert req.custom_prompt is None


def test_max_lengths_accepted():
    req = AdVariantImageEditCreate.model_validate(
        _payload(image_name="a" * 255, id_base_image="b" * 255, custom_prompt="c" * 2000)
    )
    assert len(req.image_name) == 255
    assert len(req.id_base_image) == 255
    assert len(req.custom_prompt) == 2000


# ── Invalid payloads (Req 1.3–1.7, 1.10, 1.11) ─────────────────────────────

def test_each_missing_required_field_is_rejected_with_its_loc():
    for field in _REQUIRED:
        payload = _payload()
        del payload[field]
        _assert_rejected_on(payload, field)


def test_non_convertible_int_rejected_with_its_loc():
    for field in _INT_FIELDS:
        _assert_rejected_on(_payload(**{field: "abc"}), field)


def test_id_zero_rejected_with_its_loc():
    for field in _ID_FIELDS:
        _assert_rejected_on(_payload(**{field: 0}), field)


def test_n_variations_out_of_range_rejected():
    for n in (0, 11):
        _assert_rejected_on(_payload(n_variations=n), "n_variations")


def test_missing_prompt_and_option_rejected():
    for prompt in (None, "", "   "):
        try:
            AdVariantImageEditCreate.model_validate(
                _payload(custom_prompt=prompt, expand_zoom_option=None)
            )
        except ValidationError as exc:
            msg = str(exc)
            assert "custom_prompt" in msg and "expand_zoom_option" in msg
        else:
            raise AssertionError(f"custom_prompt={prompt!r} without option accepted")


def test_blank_required_strings_rejected_with_their_loc():
    for field in ("image_name", "id_base_image"):
        for blank in ("", "   "):
            _assert_rejected_on(_payload(**{field: blank}), field)


def test_over_max_lengths_rejected_with_their_loc():
    _assert_rejected_on(_payload(image_name="a" * 256), "image_name")
    _assert_rejected_on(_payload(id_base_image="b" * 256), "id_base_image")
    _assert_rejected_on(_payload(custom_prompt="c" * 2001), "custom_prompt")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ad-variant image edit schema tests passed")
