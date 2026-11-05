"""Unit tests for the --seed mode of scripts/langfuse_update_prompt_contract.py.
The Langfuse client is replaced by an in-memory fake: no network calls.
Validates: Requirements 13.1
"""
import importlib.util
import pathlib
from unittest.mock import patch

import pytest
from langfuse.api import NotFoundError

import agents.validador_adset_agent as adset_module

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "langfuse_update_prompt_contract.py"
_spec = importlib.util.spec_from_file_location("langfuse_update_prompt_contract", _SCRIPT)
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)


class _Existing:
    version, labels, config, prompt = 3, ["latest"], {"model": "x"}, "EXISTING"


class _Created:
    version, labels = 1, ["latest"]


class _FakeLangfuse:
    def __init__(self, exists: bool):
        self.exists = exists
        self.created: list[dict] = []
        self.get_calls: list[str] = []

    def clear_prompt_cache(self):
        pass

    def get_prompt(self, name, **kwargs):
        self.get_calls.append(name)
        if not self.exists:
            raise NotFoundError(body={"message": "not found"})
        return _Existing()

    def create_prompt(self, **kwargs):
        self.created.append(kwargs)
        return _Created()

    def flush(self):
        pass


def _run(argv, fake):
    with patch.object(script, "_client", return_value=fake):
        return script.main(argv)


def test_seed_missing_prompt_apply_publishes_fallback():
    fake = _FakeLangfuse(exists=False)
    assert _run(["--prompt", "fury.validador_adset", "--seed", "--apply"], fake) == 0
    assert fake.created == [{
        "name": "fury.validador_adset",
        "prompt": adset_module._FALLBACK_INSTRUCTION,
        "labels": [],
        "type": "text",
        "config": {"model": adset_module.FALLBACK_MODEL},
        "commit_message": "Seed from fallback instruction",
    }]


def test_seed_missing_prompt_is_dry_run_by_default():
    fake = _FakeLangfuse(exists=False)
    assert _run(["--prompt", "fury.validador_adset", "--seed"], fake) == 0
    assert fake.created == []


def test_seed_existing_prompt_does_nothing():
    fake = _FakeLangfuse(exists=True)
    assert _run(["--prompt", "fury.validador_adset", "--seed", "--apply"], fake) == 0
    assert fake.created == []


@pytest.mark.parametrize("argv", [
    ["--prompt", "fury.copywriter", "--seed"],                 # seed limited to SEED_PROMPTS
    ["--prompt", "fury.validador_adset"],                      # validador_adset needs --seed
    ["--prompt", "fury.validador_adset", "--seed", "--restore", "x.txt"],
])
def test_invalid_combinations_exit_before_contacting_langfuse(argv):
    fake = _FakeLangfuse(exists=False)
    with pytest.raises(SystemExit):
        _run(argv, fake)
    assert fake.get_calls == [] and fake.created == []


def test_existing_prompts_unchanged():
    assert set(script.PROMPTS) == {"fury.estratega", "fury.copywriter", "fury.image_prompter"}
    assert set(script.SEED_PROMPTS) == {"fury.validador_adset"}
