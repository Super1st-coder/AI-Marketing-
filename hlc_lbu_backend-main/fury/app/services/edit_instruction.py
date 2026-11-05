"""Deterministic translation of ExpandZoomOption → NanoBanana2 edit instruction.

Part of the ad-variant image-edit pipeline (services/job_runner_service.py).
Pure functions: no LLM, no randomness, no clock, no request context (Req 6.5).
"""
from schemas.pipeline_schemas import ExpandZoomOption

_PRESERVE_CLAUSE = (
    "Keep the exact original aspect ratio of the base image. "
    "Do not modify, move, recolor or remove any existing content of the base image; "
    "it may only be scaled down uniformly to make room. "
    "The new content must continue the existing scene seamlessly."
)

EXPANSION_INSTRUCTIONS: dict[ExpandZoomOption, str] = {
    ExpandZoomOption.TOP: (
        "Expand the image upward: generate new content only on the top side, "
        "above the current top edge. Do not add content on the bottom, left or right sides. "
        + _PRESERVE_CLAUSE
    ),
    ExpandZoomOption.BOTTOM: (
        "Expand the image downward: generate new content only on the bottom side, "
        "below the current bottom edge. Do not add content on the top, left or right sides. "
        + _PRESERVE_CLAUSE
    ),
    ExpandZoomOption.LEFT: (
        "Expand the image to the left: generate new content only on the left side, "
        "beyond the current left edge. Do not add content on the top, bottom or right sides. "
        + _PRESERVE_CLAUSE
    ),
    ExpandZoomOption.RIGHT: (
        "Expand the image to the right: generate new content only on the right side, "
        "beyond the current right edge. Do not add content on the top, bottom or left sides. "
        + _PRESERVE_CLAUSE
    ),
    ExpandZoomOption.ZOOM_2X: (
        "Zoom out symmetrically by a factor of 2, centered: the current image must occupy "
        "the central 1/2 of the width and height, and new content must be generated on all "
        "four sides (top, bottom, left and right). " + _PRESERVE_CLAUSE
    ),
    ExpandZoomOption.ZOOM_1_5X: (
        "Zoom out symmetrically by a factor of 1.5, centered: the current image must occupy "
        "the central 1/1.5 of the width and height, and new content must be generated on all "
        "four sides (top, bottom, left and right). " + _PRESERVE_CLAUSE
    ),
    ExpandZoomOption.ZOOM_1_25X: (
        "Zoom out symmetrically by a factor of 1.25, centered: the current image must occupy "
        "the central 1/1.25 of the width and height, and new content must be generated on all "
        "four sides (top, bottom, left and right). " + _PRESERVE_CLAUSE
    ),
}


def translate_expand_zoom_option(option: ExpandZoomOption | str) -> str:
    """Return the fixed instruction for `option`. Raises ValueError for unknown values."""
    return EXPANSION_INSTRUCTIONS[ExpandZoomOption(option)]


def build_edit_instruction(
    expand_zoom_option: ExpandZoomOption | str | None,
    custom_prompt: str | None,
) -> str:
    """Edit_Instruction (Req 6.6–6.9).

    - only option  → translation
    - only prompt  → custom_prompt (already normalized by the schema)
    - both         → translation + " " + custom_prompt
    Raises ValueError if both are None/empty (the schema prevents it upstream).
    """
    has_option = expand_zoom_option is not None
    has_prompt = bool(custom_prompt)

    if not has_option and not has_prompt:
        raise ValueError("expand_zoom_option or custom_prompt is required")
    if not has_prompt:
        return translate_expand_zoom_option(expand_zoom_option)
    if not has_option:
        return custom_prompt  # type: ignore[return-value]
    return translate_expand_zoom_option(expand_zoom_option) + " " + custom_prompt
