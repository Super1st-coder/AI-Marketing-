"""Unit tests for `job_runner_service._load_or_resolve_templates` (adset-creative-diversity,
task 22.1; P12, D18, D19; Req 4.7, 4.10–4.13).

Runs the real function on top of FakeRedis / FakeGetTemplateContext inside
`network_guard()`: no network, Redis, Sinergia or LLM.

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_job_templates.py
    PYTHONPATH=. python -m tests.test_adset_diversity_job_templates
"""
import asyncio
import json

import pytest

import services.adset_diversity as ad_mod
import services.job_runner_service as jrs
from services.adset_diversity import (
    DEFAULT_DECORATIVE_IMAGE_PATTERNS,
    extract_adset_ads,
    resolve_ad_slots,
)
from tests._diversity_pipeline_fakes import (
    FakeGetATemplateDefinition,
    FakeGetTemplateContext,
    FakeRedis,
    LogCapture,
    expected_template_order,
    make_adset_context,
    mock_template_ids,
    network_guard,
)

TASK_ID = "task-job-templates"
ID_ADSET = 7
PROJECT_ID = "test-project-id"
AD_IDS = [101, 102]
SECRET = "https://x?X-Amz-Signature=abc"


def _key():
    return jrs._cp_key(TASK_ID, ID_ADSET, "adset_templates")


def _setup(monkeypatch, *, script=None, templates=None, redis=None):
    redis = redis or FakeRedis()
    monkeypatch.setattr(jrs, "_redis", lambda: redis)
    get_tc = FakeGetTemplateContext(templates=templates, script=script)
    deps = jrs._DiversityDeps(
        get_template_context=get_tc, delete_variants=None, validate_ctas=None,
        save_ads_programmatically=None, generate_images=None, build_abyssale_payload=None,
        post_to_abyssale_and_wait=None, make_estratega_adset_agent=None,
        make_copywriter_agent=None, make_image_prompter_agent=None,
        make_validador_adset_agent=None, progress=lambda *_: None,
        template_definitions=jrs._JobTemplateDefinitions(
            FakeGetATemplateDefinition(), DEFAULT_DECORATIVE_IMAGE_PATTERNS),
    )
    ctx = make_adset_context(AD_IDS)
    job = jrs._DiversityJob(
        task=None, task_id=TASK_ID, id_adset=ID_ADSET, n_variants=2,
        project_id=PROJECT_ID, id_ad=None, custom_prompt=None, add_variant=True,
        id_variant=None, adset_context=ctx, adset_context_json=json.dumps(ctx),
    )
    slots = resolve_ad_slots(extract_adset_ads(ctx, TASK_ID), None, TASK_ID)
    return deps, job, slots, redis, get_tc


def _run(deps, job, slots):
    with network_guard(), LogCapture() as logs:
        result = asyncio.run(jrs._load_or_resolve_templates(deps, job, slots))
    return result, logs


def test_resolves_and_stores_checkpoint(monkeypatch):
    deps, job, slots, redis, get_tc = _setup(monkeypatch)
    result, _ = _run(deps, job, slots)

    ids = mock_template_ids()
    order = expected_template_order(TASK_ID)
    assert result.failure is None
    assert list(result.project_templates) == ids          # Sinergia order (Req 4.10)
    assert list(result.template_order) == order           # seeded with task_id (Req 4.11)
    assert get_tc.call_count == 1
    assert redis.load(_key()) == {"project_templates": ids, "template_order": order}
    assert redis.sets[-1].ex == jrs._CHECKPOINT_TTL


def test_valid_checkpoint_is_reused_without_resolution(monkeypatch):
    cached = {"project_templates": ["A", "B", "C"], "template_order": ["C", "A", "B"]}
    deps, job, slots, redis, get_tc = _setup(monkeypatch, redis=FakeRedis({_key(): cached}))

    def _boom(*_a, **_k):
        raise AssertionError("template_order must not run with a valid checkpoint (Req 4.12)")

    monkeypatch.setattr(ad_mod, "template_order", _boom)
    result, _ = _run(deps, job, slots)

    assert result.failure is None
    assert result.project_templates == ("A", "B", "C")
    assert result.template_order == ("C", "A", "B")
    assert get_tc.call_count == 0
    assert redis.sets == []


@pytest.mark.parametrize("cached", [
    ["A", "B"],                                                          # wrong shape
    {"project_templates": ["A", "B"]},                                   # missing order
    {"project_templates": [], "template_order": []},                     # empty
    {"project_templates": ["A", 1], "template_order": [1, "A"]},         # non-str ids
    {"project_templates": ["A", "A"], "template_order": ["A", "A"]},     # repeated
    {"project_templates": ["A", "B"], "template_order": ["A", "C"]},     # not a permutation
    {"project_templates": ["A", "B", "C"], "template_order": ["A", "B"]},  # wrong length
])
def test_invalid_checkpoint_is_ignored_and_resolved_once(monkeypatch, cached):
    deps, job, slots, redis, get_tc = _setup(monkeypatch, redis=FakeRedis({_key(): cached}))
    result, logs = _run(deps, job, slots)

    assert any("invalid adset_templates checkpoint" in m for m in logs.at_level("WARNING"))
    assert get_tc.call_count == 1
    assert result.failure is None
    assert list(result.project_templates) == mock_template_ids()
    assert list(result.template_order) == expected_template_order(TASK_ID)
    assert redis.load(_key())["template_order"] == expected_template_order(TASK_ID)


@pytest.mark.parametrize("script,templates,cause", [
    ([RuntimeError(f"secret {SECRET}")], None, "get_template_context raised RuntimeError"),
    ([{"ok": False, "error": f"boom {SECRET}"}], None, "get_template_context returned ok=False"),
    (None, [], "get_template_context returned no templates"),
])
def test_failures_return_cause_without_checkpoint(monkeypatch, script, templates, cause):
    deps, job, slots, redis, get_tc = _setup(monkeypatch, script=script, templates=templates)
    result, logs = _run(deps, job, slots)        # does not raise (Req 4.7, 4.13)

    assert result.failure == cause
    assert result.project_templates == () and result.template_order == ()
    assert get_tc.call_count == 1
    assert _key() not in redis.data
    assert redis.sets == []
    assert "X-Amz-Signature" not in logs.text    # never `str(exc)` nor raw payloads


def test_at_most_one_get_template_context_call_across_retries(monkeypatch):
    # First attempt resolves and stores; a retry of the same task_id reuses the checkpoint.
    deps, job, slots, redis, get_tc = _setup(monkeypatch)
    first, _ = _run(deps, job, slots)
    second, _ = _run(deps, job, slots)
    assert second == first
    assert get_tc.call_count == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
