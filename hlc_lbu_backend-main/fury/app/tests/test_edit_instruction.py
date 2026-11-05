"""Unit tests for services/edit_instruction.py (ad-variant image-edit pipeline).

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.6, 6.7, 6.8, 13.4, 13.5

Run:
    PYTHONPATH=. pytest tests/test_edit_instruction.py
    PYTHONPATH=. python -m tests.test_edit_instruction
"""
from schemas.pipeline_schemas import ExpandZoomOption
from services.edit_instruction import (
    _PRESERVE_CLAUSE,
    EXPANSION_INSTRUCTIONS,
    build_edit_instruction,
    translate_expand_zoom_option,
)

_SIDES = {
    ExpandZoomOption.TOP: "top",
    ExpandZoomOption.BOTTOM: "bottom",
    ExpandZoomOption.LEFT: "left",
    ExpandZoomOption.RIGHT: "right",
}
_ZOOM_FACTORS = {
    ExpandZoomOption.ZOOM_2X: "factor of 2,",
    ExpandZoomOption.ZOOM_1_5X: "factor of 1.5,",
    ExpandZoomOption.ZOOM_1_25X: "factor of 1.25,",
}


def test_seven_translations_non_empty_and_distinct():
    # Req 6.1 / 13.4: every option has exactly one fixed, non-empty, distinct text.
    assert set(EXPANSION_INSTRUCTIONS) == set(ExpandZoomOption)
    texts = [translate_expand_zoom_option(o) for o in ExpandZoomOption]
    assert len(texts) == 7
    assert all(isinstance(t, str) and t.strip() for t in texts)
    assert len(set(texts)) == 7


def test_translation_is_deterministic_and_accepts_str_value():
    # Req 13.4: two calls with the same value yield the same string.
    for option in ExpandZoomOption:
        first = translate_expand_zoom_option(option)
        assert translate_expand_zoom_option(option) == first
        assert translate_expand_zoom_option(option.value) == first
        assert first == EXPANSION_INSTRUCTIONS[option]


def test_every_translation_has_aspect_ratio_and_no_modify_clauses():
    # Req 6.2
    for option in ExpandZoomOption:
        text = translate_expand_zoom_option(option)
        assert _PRESERVE_CLAUSE in text
        lowered = text.lower()
        assert "aspect ratio" in lowered
        assert "do not modify" in lowered


def test_side_options_name_their_side_explicitly():
    # Req 6.3
    for option, side in _SIDES.items():
        text = translate_expand_zoom_option(option)
        assert f"only on the {side} side" in text
        # No other side is targeted for new content.
        for other in set(_SIDES.values()) - {side}:
            assert f"only on the {other} side" not in text


def test_zoom_options_state_explicit_factor_and_four_sides():
    # Req 6.4
    for option, factor in _ZOOM_FACTORS.items():
        text = translate_expand_zoom_option(option)
        assert factor in text
        assert "symmetrically" in text and "centered" in text
        assert "all four sides" in text
        for other_option, other_factor in _ZOOM_FACTORS.items():
            if other_option is not option:
                assert other_factor not in text


def test_build_only_option_returns_translation():
    # Req 6.6
    for option in ExpandZoomOption:
        assert build_edit_instruction(option, None) == EXPANSION_INSTRUCTIONS[option]


def test_build_only_custom_prompt_returns_prompt_unchanged():
    # Req 6.7
    prompt = "Cambia el fondo a una playa al atardecer"
    assert build_edit_instruction(None, prompt) == prompt


def test_build_both_concatenates_with_single_space():
    # Req 6.8 / 13.5
    prompt = "Add warm lighting"
    for option in ExpandZoomOption:
        result = build_edit_instruction(option, prompt)
        assert result == EXPANSION_INSTRUCTIONS[option] + " " + prompt


def test_build_none_none_raises_value_error():
    try:
        build_edit_instruction(None, None)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for (None, None)")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all edit-instruction tests passed")
