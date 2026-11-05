"""Unit tests for POST /api/v2/variants/run-local (adset-creative-diversity,
Req 10.1, 10.2, 10.3, 10.4, 12.12).

`_run_phase1` (as imported by `api.v2.endpoints.variants`) and
`run_pipeline_phase1.apply_async` are replaced by in-memory fakes; network
access is blocked.

Runnable two ways:
    python -m tests.test_variants_run_local
    pytest tests/test_variants_run_local.py
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import uuid

import pytest

from tests.test_variant_create_validation_properties import (
    GOOD_HEADERS,
    PIPELINE_PARAMS,
    RUN_LOCAL_URL,
    Phase1Spy,
    variants_env,
)

# Scenario_2 (replace) payload: every one of the 7 parameters has a non-default value.
REPLACE_PAYLOAD = {
    "id_adset": 295,
    "n_variants": 2,
    "project_id": "proj-42",
    "id_ad": 1001,
    "custom_prompt": "Make it warmer",
    "add_variant": False,
    "id_variant": [11, 12, 13],
}
# Scenario_1 (add) payload.
ADD_PAYLOAD = {"id_adset": 7, "n_variants": 3, "project_id": "proj-1", "add_variant": True}
ADD_EXPECTED = {
    "id_adset": 7, "n_variants": 3, "project_id": "proj-1", "id_ad": 0,
    "custom_prompt": None, "add_variant": True, "id_variant": None,
}

SECRET_URL = "https://storage.example.com/a.png?X-Goog-Signature=deadbeef"


class PipelineBoom(Exception):
    """Custom exception raised by the fake pipeline."""


def _assert_single_call(env, expected: dict) -> dict:
    assert env.apply_async.call_count == 0
    assert env.phase1.call_count == 1
    call = env.phase1.calls[0]
    assert set(call) == {"task", "task_id", *PIPELINE_PARAMS}
    assert call["task"] is None
    parsed = uuid.UUID(call["task_id"])
    assert parsed.version == 4 and str(parsed) == call["task_id"]
    assert {k: call[k] for k in PIPELINE_PARAMS} == expected
    return call


# Req 10.1, 12.12 — the 7 parameters reach _run_phase1 unmodified
@pytest.mark.parametrize("flag", [True, False])
def test_propagates_all_seven_params_replace_mode(flag):
    with variants_env(diversity_flag=flag) as env:
        resp = env.client.post(RUN_LOCAL_URL, json=REPLACE_PAYLOAD, headers=GOOD_HEADERS)
        assert resp.status_code == 200, resp.text
        _assert_single_call(env, REPLACE_PAYLOAD)


def test_propagates_defaults_add_mode():
    with variants_env(diversity_flag=True) as env:
        resp = env.client.post(RUN_LOCAL_URL, json=ADD_PAYLOAD, headers=GOOD_HEADERS)
        assert resp.status_code == 200, resp.text
        _assert_single_call(env, ADD_EXPECTED)


def test_fresh_task_id_per_request():
    with variants_env(diversity_flag=True) as env:
        for _ in range(2):
            env.client.post(RUN_LOCAL_URL, json=ADD_PAYLOAD, headers=GOOD_HEADERS)
        ids = [c["task_id"] for c in env.phase1.calls]
        assert len(ids) == 2 and ids[0] != ids[1]


# Req 10.2 — 200 with {"ok": 1, "data": <result>}
def test_success_returns_ok_envelope_with_result():
    result = {"variant_job_id": "abc", "id_adset": 295, "status": "COMPLETED",
              "proposals": [{"id": 1}], "saved_ads": [], "diversity_reports": []}
    with variants_env(diversity_flag=True, phase1=Phase1Spy(result=result)) as env:
        resp = env.client.post(RUN_LOCAL_URL, json=REPLACE_PAYLOAD, headers=GOOD_HEADERS)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ok": 1, "data": result}


# Req 10.4, 12.12 — DEBUG=False → 404 without invoking _run_phase1
@pytest.mark.parametrize("payload", [REPLACE_PAYLOAD, ADD_PAYLOAD])
def test_debug_false_returns_404_without_calling_pipeline(payload):
    with variants_env(diversity_flag=True, debug=False) as env:
        resp = env.client.post(RUN_LOCAL_URL, json=payload, headers=GOOD_HEADERS)
        assert resp.status_code == 404, resp.text
        assert env.phase1.call_count == 0
        assert env.apply_async.call_count == 0


# Req 10.3 — 500 whose detail is only the exception class name
@pytest.mark.parametrize("error", [
    ValueError(f"download failed for {SECRET_URL}"),
    RuntimeError("api_key=sk-live-SECRET123"),
    PipelineBoom(""),
])
def test_exception_returns_500_with_class_name_only(error):
    with variants_env(diversity_flag=True, phase1=Phase1Spy(error=error)) as env:
        resp = env.client.post(RUN_LOCAL_URL, json=REPLACE_PAYLOAD, headers=GOOD_HEADERS)
        assert resp.status_code == 500, resp.text
        assert resp.json() == {"detail": type(error).__name__}
        assert "X-Goog-Signature" not in resp.text
        assert "sk-live-SECRET123" not in resp.text
        assert env.phase1.call_count == 1


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
