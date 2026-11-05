"""Unit tests for VariantCreate input validation on POST /api/v2/variants and
POST /api/v2/variants/run-local (adset-creative-diversity, Req 1.1, 1.10, 12.11).

Every rejection is checked to make 0 calls to `apply_async` and `_run_phase1`
(both replaced by in-memory fakes; network access is blocked).

Runnable two ways:
    python -m tests.test_variant_create_validation
    pytest tests/test_variant_create_validation.py
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from typing import Any

import pytest
from pydantic import ValidationError

from schemas.pipeline_schemas import VariantCreate
from tests.test_variant_create_validation_properties import (
    GOOD_HEADERS,
    RUN_LOCAL_URL,
    VARIANTS_URL,
    detail_fields,
    variants_env,
)

ENDPOINTS = ((VARIANTS_URL, 201), (RUN_LOCAL_URL, 200))

# Minimal payload accepted with the Diversity_Flag on (add-mode, default add_variant=True).
BASE = {"id_adset": 7, "n_variants": 2, "project_id": "proj-1"}


def _post(url: str, payload: dict[str, Any], *, flag: bool = True,
          headers: dict[str, str] | None = GOOD_HEADERS):
    with variants_env(diversity_flag=flag) as env:
        kwargs: dict[str, Any] = {"json": payload}
        if headers is not None:
            kwargs["headers"] = headers
        resp = env.client.post(url, **kwargs)
        return resp, env.apply_async.call_count, env.phase1.call_count


def _assert_rejected_422(url: str, payload: dict[str, Any], field: str, *, flag: bool = True) -> None:
    resp, n_async, n_phase1 = _post(url, payload, flag=flag)
    assert resp.status_code == 422, f"{url} {payload}: {resp.status_code} {resp.text}"
    assert field in detail_fields(resp.json()["detail"]), resp.text
    assert n_async == 0 and n_phase1 == 0


def _assert_accepted(url: str, ok_status: int, payload: dict[str, Any], *, flag: bool = True) -> None:
    resp, n_async, n_phase1 = _post(url, payload, flag=flag)
    assert resp.status_code == ok_status, f"{url} {payload}: {resp.status_code} {resp.text}"
    if url == VARIANTS_URL:
        assert (n_async, n_phase1) == (1, 0)
    else:
        assert (n_async, n_phase1) == (0, 1)


# ---------------------------------------------------------------------------
# Req 1.1 — field declarations / defaults unchanged
# ---------------------------------------------------------------------------

def test_variant_create_defaults_intact():
    fields = VariantCreate.model_fields
    expected_defaults = {
        "id_adset": 0, "n_variants": 3, "project_id": None, "idempotency_key": None,
        "id_ad": 0, "custom_prompt": None, "add_variant": True, "id_variant": None,
    }
    assert set(fields) == set(expected_defaults)
    for name, default in expected_defaults.items():
        assert fields[name].default == default, name
    # ge constraints preserved
    def _ge(name: str):
        return next((m.ge for m in fields[name].metadata if hasattr(m, "ge")), None)
    assert _ge("id_adset") == 0
    assert _ge("n_variants") == 1
    assert _ge("id_ad") == 0


def test_variant_create_model_validator_raises_on_default_id_adset(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "USE_ADSET_CREATIVE_DIVERSITY", False)
    with pytest.raises(ValidationError):
        VariantCreate()
    assert VariantCreate(id_adset=1).n_variants == 3


# ---------------------------------------------------------------------------
# Req 12.11 — rejections (422) on both endpoints
# ---------------------------------------------------------------------------

REJECTION_CASES = [
    ("replace_without_id_variant", {**BASE, "add_variant": False, "id_ad": 5}, "id_variant"),
    ("replace_with_empty_id_variant", {**BASE, "add_variant": False, "id_ad": 5, "id_variant": []}, "id_variant"),
    ("replace_null_add_variant_without_id_variant", {**BASE, "add_variant": None, "id_ad": 5}, "id_variant"),
    ("id_variant_value_below_1_replace", {**BASE, "add_variant": False, "id_ad": 5, "id_variant": [3, 0]}, "id_variant"),
    ("id_variant_value_below_1_add", {**BASE, "id_variant": [-1]}, "id_variant"),
    ("replace_with_id_ad_none", {**BASE, "add_variant": False, "id_ad": None, "id_variant": [1]}, "id_ad"),
    ("replace_with_id_ad_zero", {**BASE, "add_variant": False, "id_ad": 0, "id_variant": [1]}, "id_ad"),
    ("n_variants_zero", {**BASE, "n_variants": 0}, "n_variants"),
    ("id_adset_zero", {**BASE, "id_adset": 0}, "id_adset"),
    ("id_adset_omitted", {"n_variants": 2, "project_id": "proj-1"}, "id_adset"),
    ("id_adset_negative", {**BASE, "id_adset": -1}, "id_adset"),
    ("id_ad_negative", {**BASE, "id_ad": -2}, "id_ad"),
    ("id_adset_bad_type", {**BASE, "id_adset": "abc"}, "id_adset"),
    ("n_variants_bad_type", {**BASE, "n_variants": "many"}, "n_variants"),
    ("id_variant_bad_type", {**BASE, "add_variant": False, "id_ad": 5, "id_variant": ["x"]}, "id_variant"),
    ("add_variant_bad_type", {**BASE, "add_variant": "maybe"}, "add_variant"),
    ("project_id_missing_flag_on", {"id_adset": 7}, "project_id"),
    ("project_id_empty_flag_on", {"id_adset": 7, "project_id": ""}, "project_id"),
    ("project_id_blank_flag_on", {"id_adset": 7, "project_id": "   "}, "project_id"),
]


@pytest.mark.parametrize("url,_ok", ENDPOINTS)
@pytest.mark.parametrize("name,payload,field", REJECTION_CASES, ids=[c[0] for c in REJECTION_CASES])
def test_invalid_payload_rejected_422(url, _ok, name, payload, field):
    _assert_rejected_422(url, payload, field, flag=True)


# ---------------------------------------------------------------------------
# Acceptance cases
# ---------------------------------------------------------------------------

ACCEPT_CASES = [
    ("add_mode_minimal", BASE, True),
    ("id_variant_shorter_than_n_variants", {**BASE, "n_variants": 4, "add_variant": False, "id_ad": 5, "id_variant": [10]}, True),
    ("id_variant_longer_than_n_variants", {**BASE, "n_variants": 1, "add_variant": False, "id_ad": 5, "id_variant": [10, 11, 12]}, True),
    ("project_id_missing_flag_off", {"id_adset": 7}, False),
    ("project_id_blank_flag_off", {"id_adset": 7, "project_id": "  "}, False),
]


@pytest.mark.parametrize("url,ok_status", ENDPOINTS)
@pytest.mark.parametrize("name,payload,flag", ACCEPT_CASES, ids=[c[0] for c in ACCEPT_CASES])
def test_valid_payload_accepted(url, ok_status, name, payload, flag):
    _assert_accepted(url, ok_status, payload, flag=flag)


# ---------------------------------------------------------------------------
# Req 1.10 — X-Internal-API-Key missing / invalid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,_ok", ENDPOINTS)
def test_missing_api_key_rejected(url, _ok):
    resp, n_async, n_phase1 = _post(url, BASE, headers=None)
    assert resp.status_code in (401, 403), resp.text
    assert n_async == 0 and n_phase1 == 0


@pytest.mark.parametrize("url,_ok", ENDPOINTS)
def test_invalid_api_key_rejected(url, _ok):
    resp, n_async, n_phase1 = _post(url, BASE, headers={"X-Internal-API-Key": "wrong-key"})
    assert resp.status_code == 401, resp.text
    assert n_async == 0 and n_phase1 == 0


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
