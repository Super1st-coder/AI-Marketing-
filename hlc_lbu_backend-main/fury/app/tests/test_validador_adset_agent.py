"""Unit tests for the Validador_Adset agent (fury.validador_adset).

Validates: Requirements 13.1, 13.3, 13.5, 12.22, 12.27
"""
import inspect
from unittest.mock import patch

from google.adk.agents import Agent

import agents.validador_adset_agent as adset_module
import agents.validador_agent as legacy_module
from agents.guards import safety_guard_after_model, safety_guard_before_model
from agents.tools.validation_tools import check_diversity_and_fidelity
from core.config import settings

_FAKE_CFG = {"instruction": "LANGFUSE ADSET INSTRUCTION", "model": "gemini/gemini-2.5-flash"}


# ── Factory (Req 13.1, 13.3) ───────────────────────────────────────────────────

def test_factory_requests_langfuse_config_with_fallbacks():
    with patch.object(adset_module, "get_agent_config_from_langfuse", return_value=dict(_FAKE_CFG)) as cfg:
        adset_module.make_validador_adset_agent()

    cfg.assert_called_once()
    args, kwargs = cfg.call_args
    assert args[0] == "fury.validador_adset"
    assert args[1] == adset_module._FALLBACK_INSTRUCTION
    assert kwargs["fallback_model"] == "gemini/gemini-2.5-flash"
    assert kwargs["cache_ttl_seconds"] == settings.LANGFUSE_CACHE_TTL_SECONDS


def test_factory_builds_agent_without_tools_and_with_guards():
    with patch.object(adset_module, "get_agent_config_from_langfuse", return_value=dict(_FAKE_CFG)):
        agent = adset_module.make_validador_adset_agent()

    assert isinstance(agent, Agent)
    assert agent.name == "validador_adset_agent"
    assert agent.tools == []
    assert agent.instruction == _FAKE_CFG["instruction"]
    assert agent.before_model_callback is safety_guard_before_model
    assert agent.after_model_callback is safety_guard_after_model


def test_factory_does_not_accept_custom_prompt():
    assert list(inspect.signature(adset_module.make_validador_adset_agent).parameters) == []
    with patch.object(adset_module, "get_agent_config_from_langfuse", return_value=dict(_FAKE_CFG)):
        try:
            adset_module.make_validador_adset_agent("custom prompt")  # type: ignore[call-arg]
        except TypeError:
            pass
        else:
            raise AssertionError("make_validador_adset_agent must not accept custom_prompt")


# ── Fallback instruction (Req 13.3, 13.5, 12.22, 12.27) ────────────────────────

def test_fallback_instruction_contains_required_rules():
    instr = adset_module._FALLBACK_INSTRUCTION
    for fragment in (
        "share ON PURPOSE",
        "NOT a failure",
        "(a)",
        "(b)",
        "Do NOT compare variants",
        "Not following its Variant_Angle is NOT",
        "NO tools",
        "overall_pass",
        "subset_to_regenerate",
        "variant_key",
    ):
        assert fragment in instr, f"missing fragment: {fragment!r}"


# ── Legacy validador untouched (Req 13.1) ──────────────────────────────────────

def test_legacy_validador_keeps_diversity_tool():
    with patch.object(legacy_module, "get_agent_config_from_langfuse", return_value=dict(_FAKE_CFG)):
        agent = legacy_module.make_validador_agent()
    assert agent.tools == [check_diversity_and_fidelity]


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
