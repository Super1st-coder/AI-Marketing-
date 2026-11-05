"""PersonaVariantsPrompter validator — accepts both the "variants" key (per the agent
instruction + pipeline) and the legacy "variations" spelling.

Regression: gemini-2.5-pro emits "variants" per the instruction, but the validator only
checked "variations", failing with "Missing or empty 'variations' array".
"""
import json

from services.persona_validators import validate_persona_variants_prompter_response

_TYPES = ["Frontal", "Side Face", "Expression", "Full Body", "Outfit"]


def _payload(array_key: str) -> str:
    return json.dumps({
        "master_prompt": "a cinematic persona portrait",
        array_key: [
            {"plan_id": f"v{i}", "variant_type": t, "image_prompts": [{"image_prompt": "x"}]}
            for i, t in enumerate(_TYPES, start=1)
        ],
    })


def test_accepts_variants_key():
    result = validate_persona_variants_prompter_response(_payload("variants"))
    assert result.is_valid


def test_accepts_legacy_variations_key():
    result = validate_persona_variants_prompter_response(_payload("variations"))
    assert result.is_valid


def test_rejects_when_array_missing():
    result = validate_persona_variants_prompter_response(json.dumps({"master_prompt": "x"}))
    assert not result.is_valid
    assert any("variants" in e for e in result.errors)
