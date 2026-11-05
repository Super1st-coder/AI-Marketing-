"""Deterministic character-limit enforcement for generated ad copy.

The Copywriter agent is *instructed* to respect each element's character limit,
but an LLM will overflow those limits sooner or later — and when it does, the
extra characters overflow the Abyssale-rendered frame (the "system generates too
many long MaxChar details" problem). Prompt guidance is necessary but never a
guarantee.

This module is the deterministic guarantee: it truncates any overlay text that
exceeds its element's limit — at a word boundary — *before* the copy is mapped
into the Abyssale payload. It runs in code, not in the model, so it cannot be
talked out of enforcing the limit.

Limit resolution (priority order), see :func:`resolve_limit`:
  1. An explicit per-element override (the real template / channel spec, when
     the caller has it on hand).
  2. :data:`DEFAULT_ELEMENT_LIMITS`, keyed by the standard channel field name —
     the documented, stable limits for the core text slots.
  3. No known limit -> the text is left untouched. We never truncate blindly.

Buttons/CTAs are intentionally NOT truncated here: their value must match a CTA
option exactly (see the Copywriter's get_ctas contract), and clipping it would
corrupt that exact-match requirement.
"""
from core.logging import get_logger

logger = get_logger(__name__)


# Documented channel text limits (see root_orchestrator output contract:
# channel_attributes -> max_char per element name). These are the stable
# fallbacks used whenever a caller does not supply the live template spec.
DEFAULT_ELEMENT_LIMITS: dict[str, int] = {
    "primary_text": 80,
    "headline": 27,
    "description": 27,
}


def _normalize(key: object) -> str:
    """Lowercase + collapse separators so 'Primary Text' == 'primary_text'."""
    return str(key or "").strip().lower().replace("-", "_").replace(" ", "_")


def resolve_limit(element_key: object, overrides: dict | None = None) -> int | None:
    """Resolve the character limit for an element, or None if unknown.

    Matching is forgiving: an exact normalized match wins, then a substring
    match against a known field name (so 'ad_headline' / 'headline_1' still
    resolve to the headline limit). Unknown elements return None -> untouched.
    """
    norm = _normalize(element_key)
    if not norm:
        return None

    # 1. Explicit override from the live spec (normalized keys).
    if overrides:
        norm_overrides = {_normalize(k): v for k, v in overrides.items()}
        if norm in norm_overrides and _is_positive_int(norm_overrides[norm]):
            return int(norm_overrides[norm])

    # 2. Default table — exact, then substring.
    if norm in DEFAULT_ELEMENT_LIMITS:
        return DEFAULT_ELEMENT_LIMITS[norm]
    for name, limit in DEFAULT_ELEMENT_LIMITS.items():
        if name in norm:
            return limit

    # 3. Unknown -> no enforcement.
    return None


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def fit_to_limit(text: str, max_char: int) -> str:
    """Return `text` trimmed to at most `max_char` chars, at a word boundary.

    - No-op when `max_char` is falsy/<=0 or the text already fits.
    - Prefers cutting at the last whitespace so words are not split; falls back
      to a hard cut when there is no whitespace in range.
    - Never appends an ellipsis — the result is guaranteed <= max_char.
    """
    if not isinstance(text, str) or not _is_positive_int(max_char):
        return text
    if len(text) <= max_char:
        return text

    window = text[:max_char]
    cut = window.rsplit(" ", 1)[0].rstrip()
    # Prefer a clean word boundary — but only when it keeps most of the budget.
    # On very tight limits (e.g. a 9-char field) the last-space cut can throw away
    # almost everything ("EL SEMAFORO…" -> "EL"); there a hard cut that fills the
    # frame reads better. Fall back to a hard cut when the word-boundary result
    # keeps less than 60% of the available characters, or ate everything.
    if not cut or len(cut) < max_char * 0.6:
        cut = window.rstrip()
    return cut


def enforce_element_limits(
    template_elements: list[dict],
    overrides: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    """Fit every free-text element's `text` to its resolved limit.

    Args:
        template_elements: the Copywriter's SECTION-2 elements, each shaped like
            {"element_id"/"element_type"/"text", ...}.
        overrides: optional {element_key: max_char} from the live spec.

    Returns:
        (fitted_elements, truncations) — `fitted_elements` is a new list with
        over-length `text` trimmed; `truncations` records what was clipped
        ({element_id, limit, original_len, new_len}) for logging/telemetry.

    Buttons (element_type == "button") are passed through unchanged.
    """
    fitted: list[dict] = []
    truncations: list[dict] = []

    for element in template_elements or []:
        if not isinstance(element, dict):
            fitted.append(element)
            continue

        new_element = dict(element)
        element_type = _normalize(element.get("element_type"))
        text = element.get("text")

        if element_type == "button" or not isinstance(text, str):
            fitted.append(new_element)
            continue

        element_key = element.get("element_id") or element.get("element_type")
        limit = resolve_limit(element_key, overrides)
        if limit is not None and len(text) > limit:
            new_element["text"] = fit_to_limit(text, limit)
            truncations.append({
                "element_id": element.get("element_id"),
                "limit": limit,
                "original_len": len(text),
                "new_len": len(new_element["text"]),
            })
        fitted.append(new_element)

    if truncations:
        detail = "; ".join(
            f"{t['element_id']} {t['original_len']}->{t['new_len']} (max {t['limit']})"
            for t in truncations
        )
        logger.warning(
            f"MaxChar enforcement trimmed {len(truncations)} over-length element(s): {detail}"
        )
    return fitted, truncations
