"""Property-based tests for services/edit_instruction.py (ad-variant-image-edit pipeline).

Run with:
    PYTHONPATH=. pytest tests/test_edit_instruction_properties.py
    PYTHONPATH=. python -m tests.test_edit_instruction_properties
"""
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from schemas.pipeline_schemas import ExpandZoomOption
from services.edit_instruction import build_edit_instruction, translate_expand_zoom_option

# Normalized custom_prompt: non-empty, already stripped, ≤ 2000 chars (schema output).
_normalized_prompts = (
    st.text(min_size=1, max_size=2000)
    .map(str.strip)
    .filter(lambda s: len(s) > 0)
)
_options = st.sampled_from(list(ExpandZoomOption)) | st.none()
_prompts = _normalized_prompts | st.none()


# Feature: ad-variant-image-edit-pipeline, Property 3: Composición determinista de la Edit_Instruction
@settings(max_examples=100, deadline=None)
@given(option=_options, prompt=_prompts, as_str=st.booleans())
def test_edit_instruction_deterministic_composition(option, prompt, as_str):
    """**Validates: Requirements 6.5, 6.6, 6.7, 6.8, 6.9, 13.3, 13.4, 13.5**"""
    # The pipeline may receive the option as enum or as its JSON str value (Celery kwargs).
    arg_option = option.value if (as_str and option is not None) else option

    if option is None and prompt is None:
        with pytest.raises(ValueError):
            build_edit_instruction(arg_option, prompt)
        return

    result = build_edit_instruction(arg_option, prompt)

    if prompt is None:
        expected = translate_expand_zoom_option(option)
    elif option is None:
        expected = prompt
    else:
        expected = translate_expand_zoom_option(option) + " " + prompt
    assert result == expected

    # Same input → identical string, character by character (Req 6.9, retries).
    assert build_edit_instruction(arg_option, prompt) == result
    # Enum vs str form of the option are interchangeable.
    assert build_edit_instruction(option, prompt) == result


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all edit-instruction property tests passed")
