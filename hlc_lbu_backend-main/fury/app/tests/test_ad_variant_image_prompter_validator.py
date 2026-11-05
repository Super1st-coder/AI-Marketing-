"""Unit tests for the ad_variant_image_prompter agent and its validator.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 13.17
"""
import importlib
import json
from unittest.mock import patch

from google.adk.agents import Agent

import agents.ad_variant_image_prompter_agent as prompter_module
from agents.guards import safety_guard_after_model, safety_guard_before_model
from core.config import settings
from services.ads_validators import validate_ad_variant_image_prompter_response


# ── Validator (Req 8.5, 8.6, 13.17) ────────────────────────────────────────────

def test_valid_image_prompt_returns_parsed_data():
    payload = {"image_prompt": "A red sneaker on a white studio background."}
    result = validate_ad_variant_image_prompter_response(json.dumps(payload))
    assert result.is_valid
    assert result.data == payload


def test_valid_with_exactly_2000_chars():
    result = validate_ad_variant_image_prompter_response(json.dumps({"image_prompt": "a" * 2000}))
    assert result.is_valid


def test_missing_image_prompt_is_invalid():
    result = validate_ad_variant_image_prompter_response(json.dumps({"prompt": "x"}))
    assert not result.is_valid
    assert result.errors and any("image_prompt" in e for e in result.errors)


def test_empty_image_prompt_is_invalid():
    for value in ("", "   \n\t "):
        result = validate_ad_variant_image_prompter_response(json.dumps({"image_prompt": value}))
        assert not result.is_valid
        assert result.errors and any("empty" in e for e in result.errors)


def test_non_str_image_prompt_is_invalid():
    for value in (123, None, ["a"], {"a": "b"}, True):
        result = validate_ad_variant_image_prompter_response(json.dumps({"image_prompt": value}))
        assert not result.is_valid
        assert result.errors and any("string" in e for e in result.errors)


def test_image_prompt_over_2000_chars_is_invalid():
    result = validate_ad_variant_image_prompter_response(json.dumps({"image_prompt": "a" * 2001}))
    assert not result.is_valid
    assert result.errors and any("2000" in e for e in result.errors)


def test_non_json_text_is_invalid():
    result = validate_ad_variant_image_prompter_response("Here is a description of the image.")
    assert not result.is_valid
    assert result.errors and any("JSON" in e for e in result.errors)


def test_non_object_json_is_invalid():
    result = validate_ad_variant_image_prompter_response(json.dumps(["image_prompt"]))
    assert not result.is_valid
    assert result.errors


# ── Factory (Req 8.1–8.4) ──────────────────────────────────────────────────────

_FAKE_CFG = {"instruction": "LANGFUSE INSTRUCTION", "model": "gemini/gemini-2.5-flash"}


def test_factory_uses_langfuse_config_and_builds_agent():
    with patch.object(prompter_module, "get_agent_config_from_langfuse", return_value=dict(_FAKE_CFG)) as cfg:
        agent = prompter_module.make_ad_variant_image_prompter_agent()

    cfg.assert_called_once()
    args, kwargs = cfg.call_args
    assert args[0] == "fury.ad_variant_image_prompter"
    assert args[1] == prompter_module._FALLBACK_INSTRUCTION
    assert kwargs["fallback_model"].startswith("gemini/")
    assert kwargs["cache_ttl_seconds"] == settings.LANGFUSE_CACHE_TTL_SECONDS

    assert isinstance(agent, Agent)
    assert agent.name == "ad_variant_image_prompter"
    assert agent.tools == []
    assert agent.before_model_callback is safety_guard_before_model
    assert agent.after_model_callback is safety_guard_after_model
    assert agent.instruction.startswith("LANGFUSE INSTRUCTION")
    assert agent.model.model == "gemini/gemini-2.5-flash"
    assert "/" in agent.model.model  # provider prefix preserved


def test_factory_appends_custom_prompt():
    with patch.object(prompter_module, "get_agent_config_from_langfuse", return_value=dict(_FAKE_CFG)):
        agent = prompter_module.make_ad_variant_image_prompter_agent("focus on the product")
    assert "focus on the product" in agent.instruction


def test_fallback_instruction_requires_json_image_prompt():
    instr = prompter_module._FALLBACK_INSTRUCTION
    assert instr.strip()
    assert "image_prompt" in instr
    assert "JSON" in instr


def test_module_import_does_not_instantiate_agent():
    try:
        with patch("core.adk_config.get_agent_config_from_langfuse") as cfg:
            reloaded = importlib.reload(prompter_module)
            cfg.assert_not_called()
            assert not any(isinstance(v, Agent) for v in vars(reloaded).values())
    finally:
        importlib.reload(prompter_module)  # restore the real Langfuse binding


if __name__ == "__main__":
    import sys

    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
