"""Tests for deterministic MaxChar enforcement (services.text_limits).

Guards the fix for "the system generates too many long MaxChar details": the
Copywriter is only *asked* to respect per-element character limits, so when the
LLM overflows, the extra characters overflow the Abyssale-rendered frame. The
enforcer clips over-length overlay text at a word boundary before it reaches
Abyssale — the deterministic guarantee behind the prompt guidance.

Runnable two ways:
    python -m tests.test_text_limits      # plain asserts, prints a summary
    pytest tests/test_text_limits.py      # standard collection
"""
from __future__ import annotations

from services.text_limits import (
    DEFAULT_ELEMENT_LIMITS,
    enforce_element_limits,
    fit_to_limit,
    resolve_limit,
)


# ── fit_to_limit ────────────────────────────────────────────────────────────

def test_fit_noop_when_within_limit():
    assert fit_to_limit("Just Do It", 27) == "Just Do It"


def test_fit_trims_at_word_boundary_and_respects_limit():
    text = "Unleash your performance with the all new running shoe"
    out = fit_to_limit(text, 27)
    assert len(out) <= 27
    # cut at a space -> no split word, no trailing space
    assert not out.endswith(" ")
    assert " " not in text[:len(out)][len(out):]  # nothing after cut is a partial word


def test_fit_hard_cuts_a_single_long_token():
    out = fit_to_limit("Supercalifragilisticexpialidocious", 10)
    assert out == "Supercalif"
    assert len(out) == 10


def test_fit_fills_frame_on_very_tight_limit():
    # Real case from the Loom: a 9-char "Hook" field. A pure word-boundary cut would
    # collapse "EL SEMAFORO EN ROJO. TU NO." to just "EL"; we hard-cut to fill the frame.
    out = fit_to_limit("EL SEMAFORO EN ROJO. TU NO.", 9)
    assert out == "EL SEMAFO"
    assert len(out) <= 9


def test_fit_keeps_word_boundary_when_it_retains_enough():
    # "CARACTER QUE SE LLEVA PUESTO" @ 12 -> "CARACTER" (8 chars >= 60% of 12) stays clean.
    out = fit_to_limit("CARACTER QUE SE LLEVA PUESTO", 12)
    assert out == "CARACTER"
    assert len(out) <= 12


def test_fit_ignores_nonpositive_or_nonstring():
    assert fit_to_limit("keep me", 0) == "keep me"
    assert fit_to_limit("keep me", -5) == "keep me"
    assert fit_to_limit(None, 5) is None


# ── resolve_limit ───────────────────────────────────────────────────────────

def test_resolve_known_default_fields():
    assert resolve_limit("headline") == 27
    assert resolve_limit("primary_text") == 80
    assert resolve_limit("description") == 27


def test_resolve_is_forgiving_about_naming():
    assert resolve_limit("Primary Text") == 80          # spacing / case
    assert resolve_limit("ad_headline_1") == 27          # substring match
    assert resolve_limit("sub-headline") == 27


def test_resolve_unknown_returns_none():
    assert resolve_limit("legal_disclaimer") is None
    assert resolve_limit("") is None
    assert resolve_limit(None) is None


def test_override_wins_over_default():
    assert resolve_limit("headline", overrides={"headline": 40}) == 40
    # a bogus (non-positive / non-int) override is ignored -> falls back to default
    assert resolve_limit("headline", overrides={"headline": 0}) == 27
    assert resolve_limit("headline", overrides={"headline": "nope"}) == 27


# ── enforce_element_limits ──────────────────────────────────────────────────

def test_enforce_trims_overlength_text_element():
    elements = [
        {"element_id": "headline", "element_type": "text",
         "text": "Experience unmatched comfort and speed today"},
    ]
    fitted, truncations = enforce_element_limits(elements)
    assert len(fitted[0]["text"]) <= 27
    assert len(truncations) == 1
    assert truncations[0]["element_id"] == "headline"
    assert truncations[0]["limit"] == 27
    assert truncations[0]["original_len"] > truncations[0]["new_len"]


def test_enforce_never_touches_buttons():
    # A CTA/button value must survive verbatim (exact-match contract with get_ctas).
    elements = [
        {"element_id": "cta", "element_type": "button", "text": "COMPRAR_AHORA_CON_DESCUENTO"},
    ]
    fitted, truncations = enforce_element_limits(elements)
    assert fitted[0]["text"] == "COMPRAR_AHORA_CON_DESCUENTO"
    assert truncations == []


def test_enforce_leaves_unknown_and_fitting_elements_untouched():
    elements = [
        {"element_id": "legal", "element_type": "text", "text": "x" * 300},   # unknown -> untouched
        {"element_id": "headline", "element_type": "text", "text": "Short one"},  # fits -> untouched
    ]
    fitted, truncations = enforce_element_limits(elements)
    assert fitted[0]["text"] == "x" * 300
    assert fitted[1]["text"] == "Short one"
    assert truncations == []


def test_enforce_does_not_mutate_input():
    elements = [{"element_id": "description", "element_type": "text",
                 "text": "A very long supporting detail that clearly runs past the limit"}]
    original_text = elements[0]["text"]
    fitted, _ = enforce_element_limits(elements)
    assert elements[0]["text"] == original_text          # input untouched
    assert fitted[0]["text"] != original_text            # output trimmed


def test_enforce_uses_override_spec_when_provided():
    elements = [{"element_id": "headline", "element_type": "text",
                 "text": "This headline is definitely more than forty chars long indeed"}]
    fitted, truncations = enforce_element_limits(elements, overrides={"headline": 40})
    assert len(fitted[0]["text"]) <= 40
    assert truncations[0]["limit"] == 40


def test_defaults_match_documented_channel_spec():
    # Pin the documented channel_attributes limits so a silent edit is caught.
    assert DEFAULT_ELEMENT_LIMITS == {"primary_text": 80, "headline": 27, "description": 27}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all text-limits tests passed")
