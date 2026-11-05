"""The Adset_Context is injected by the pipeline: the Estratega, Copywriter and
Image_Prompter never get the real `get_adset_context` tool, only a no-network stub, and
their instructions tell them to read the FULL ADSET CONTEXT block instead.

Run with:
    PYTHONPATH=. pytest tests/test_injected_context.py
"""
import pytest

from agents.copywriter_agent import make_copywriter_agent
from agents.estratega_agent import make_estratega_agent
from agents.image_prompter_agent import make_image_prompter_agent
from agents.tools import injected_context
from services.adset_diversity import FULL_ADSET_CONTEXT_HEADER

FACTORIES = [make_estratega_agent, make_copywriter_agent, make_image_prompter_agent]
OLD_RULE = "Do NOT write any text before calling get_adset_context"


@pytest.fixture(autouse=True)
def _no_langfuse(monkeypatch):
    # Force the fallback instruction (the one versioned in this repo).
    import core.adk_config as adk_config
    from core.config import settings

    monkeypatch.setattr(settings, "LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setattr(settings, "LANGFUSE_SECRET_KEY", "")
    yield adk_config


@pytest.mark.parametrize("factory", FACTORIES)
def test_agents_only_have_the_stub(factory):
    agent = factory(None)
    by_name = {t.__name__: t for t in agent.tools}
    assert by_name["get_adset_context"] is injected_context.get_adset_context
    assert all(t.__module__ != "agents.tools.campaign_tools" or t.__name__ != "get_adset_context"
               for t in agent.tools)


@pytest.mark.parametrize("factory", FACTORIES)
def test_fallbacks_point_to_the_injected_block(factory):
    instruction = factory(None).instruction
    assert injected_context.CONTEXT_SOURCE_MARKER in instruction
    assert OLD_RULE not in instruction
    assert "Call get_adset_context" not in instruction


def test_stub_makes_no_network_call(monkeypatch):
    import httpx

    def boom(*args, **kwargs):
        raise AssertionError("network call")

    monkeypatch.setattr(httpx, "get", boom)
    monkeypatch.setattr(httpx, "post", boom)
    result = injected_context.get_adset_context(355)
    assert result["ok"] is False and result["error"] == "context_already_provided"
    assert injected_context.INJECTED_CONTEXT_HEADER in result["message"]


def test_section_matches_pipeline_header_and_has_no_mustache():
    # The block the pipeline injects starts with the header the section points to.
    assert FULL_ADSET_CONTEXT_HEADER.startswith(injected_context.INJECTED_CONTEXT_HEADER)
    assert "{{" not in injected_context.CONTEXT_SOURCE_SECTION


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
