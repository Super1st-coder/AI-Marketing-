"""Property-based tests for VariantCreate validation on POST /api/v2/variants
and POST /api/v2/variants/run-local (adset-creative-diversity, Req 1).

Everything runs in memory: `run_pipeline_phase1.apply_async` and `_run_phase1`
(as imported by `api.v2.endpoints.variants`) are replaced by recording fakes,
and `network_guard()` makes any real outbound call fail.

Runnable two ways:
    python -m tests.test_variant_create_validation_properties
    pytest tests/test_variant_create_validation_properties.py
"""
from __future__ import annotations

import os

# services/llm_service.py builds an OpenAI client at import time (via main).
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

import copy
import uuid
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from typing import Any, Iterator

from fastapi.testclient import TestClient
from hypothesis import given, settings as hsettings, strategies as st

from api.v2.endpoints import variants as variants_module
from core.config import settings
from main import app
from tests._edit_pipeline_fakes import DEFAULT_INTERNAL_API_KEY, AttrPatcher, network_guard

VARIANTS_URL = "/api/v2/variants"
RUN_LOCAL_URL = "/api/v2/variants/run-local"
GOOD_HEADERS = {"X-Internal-API-Key": DEFAULT_INTERNAL_API_KEY}

# The 7 parameters propagated by both endpoints to the pipeline.
PIPELINE_PARAMS = (
    "id_adset", "n_variants", "project_id", "id_ad",
    "custom_prompt", "add_variant", "id_variant",
)

OMIT = object()  # strategy sentinel → the key is left out of the JSON payload
NOT_AN_INT = "abc"  # value Pydantic v2 cannot coerce to int (Req 1.7)


# ---------------------------------------------------------------------------
# Fakes (reused by Property 2)
# ---------------------------------------------------------------------------

class FakeApplyAsync:
    """Records `apply_async` calls; returns an AsyncResult-like with a fresh id."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.ids: list[str] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def __call__(self, *args: Any, **kwargs: Any) -> SimpleNamespace:
        self.calls.append({"args": args, "kwargs": copy.deepcopy(kwargs)})
        task_id = str(uuid.uuid4())
        self.ids.append(task_id)
        return SimpleNamespace(id=task_id)


class Phase1Spy:
    """Stand-in for `_run_phase1`: records kwargs, returns `result` or raises `error`."""

    def __init__(self, result: Any = None, error: BaseException | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result = {"ads": []} if result is None else result
        self.error = error

    @property
    def call_count(self) -> int:
        return len(self.calls)

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(copy.deepcopy(kwargs))
        if self.error is not None:
            raise self.error
        return self.result


@contextmanager
def variants_env(
    *,
    diversity_flag: bool,
    debug: bool = True,
    phase1: Phase1Spy | None = None,
) -> Iterator[SimpleNamespace]:
    """Patch settings, `apply_async` and `_run_phase1` for the variants endpoints."""
    env = SimpleNamespace(apply_async=FakeApplyAsync(), phase1=phase1 or Phase1Spy())
    patcher = AttrPatcher()
    with ExitStack() as stack:
        stack.enter_context(network_guard())
        stack.callback(patcher.undo)
        patcher.set(settings, "DEBUG", debug)
        patcher.set(settings, "FURY_INTERNAL_API_KEY", DEFAULT_INTERNAL_API_KEY)
        patcher.set(settings, "USE_ADSET_CREATIVE_DIVERSITY", diversity_flag)
        patcher.set(variants_module.run_pipeline_phase1, "apply_async", env.apply_async)
        patcher.set(variants_module, "_run_phase1", env.phase1)
        env.client = TestClient(app, raise_server_exceptions=False)
        yield env


# ---------------------------------------------------------------------------
# Payload strategy and pure oracle (reused by Property 2)
# ---------------------------------------------------------------------------

def _with_omit(strategy: st.SearchStrategy) -> st.SearchStrategy:
    return st.one_of(st.just(OMIT), strategy)


_small_int = st.integers(min_value=-3, max_value=6)
_int_or_garbage = st.one_of(_small_int, st.just(NOT_AN_INT))

payload_fields = st.fixed_dictionaries({
    "id_adset": _with_omit(_int_or_garbage),
    "n_variants": _with_omit(_int_or_garbage),
    "id_ad": _with_omit(st.one_of(st.none(), _int_or_garbage)),
    "add_variant": _with_omit(st.sampled_from([True, False, None])),
    "id_variant": _with_omit(st.one_of(
        st.none(),
        st.just([]),
        st.lists(st.integers(min_value=1, max_value=500), min_size=1, max_size=8),
        st.lists(st.integers(min_value=-3, max_value=500), min_size=1, max_size=8),
    )),
    "project_id": _with_omit(st.one_of(
        st.none(),
        st.just(""),
        st.text(alphabet=" \t", min_size=1, max_size=4),
        st.text(alphabet="abcdefXYZ0123456789-_", min_size=1, max_size=12),
    )),
    "custom_prompt": _with_omit(st.one_of(st.none(), st.just("Make it warmer"))),
})


def build_payload(fields: dict[str, Any]) -> dict[str, Any]:
    """Drop OMIT keys → the JSON body sent to the endpoint."""
    return {k: v for k, v in fields.items() if v is not OMIT}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def oracle_rejected_fields(payload: dict[str, Any], diversity_flag: bool) -> set[str]:
    """Pure encoding of Req 1.2–1.8. Empty set ⇔ the request must be accepted.

    Field-level errors (types/constraints, Req 1.7) are raised by Pydantic before
    the model validator, so cross-field rules only apply when there are none.
    """
    id_adset = payload.get("id_adset", 0)
    n_variants = payload.get("n_variants", 3)
    id_ad = payload.get("id_ad", 0)
    add_variant = payload.get("add_variant", True)
    id_variant = payload.get("id_variant")
    project_id = payload.get("project_id")

    field_errors: set[str] = set()
    if not _is_int(id_adset) or id_adset < 0:
        field_errors.add("id_adset")
    if not _is_int(n_variants) or n_variants < 1:
        field_errors.add("n_variants")
    if id_ad is not None and (not _is_int(id_ad) or id_ad < 0):
        field_errors.add("id_ad")
    if field_errors:
        return field_errors

    errors: set[str] = set()
    replace = add_variant is not True  # False or explicit null
    if id_adset == 0:  # 1.6
        errors.add("id_adset")
    if id_variant and any(v < 1 for v in id_variant):  # 1.3
        errors.add("id_variant")
    if replace and not id_variant:  # 1.2
        errors.add("id_variant")
    if replace and not id_ad:  # 1.4 (None or 0)
        errors.add("id_ad")
    if diversity_flag and not (project_id or "").strip():  # 1.8
        errors.add("project_id")
    # 1.5: len(id_variant) vs n_variants is never a rejection reason.
    return errors


def detail_fields(detail: Any) -> set[str]:
    """Field names named by a FastAPI 422 detail.

    Field errors carry the field in `loc` (["body", "<field>", ...]); model-level
    errors have loc == ["body"] and a msg "Value error, <field>: ...; <field>: ...".
    """
    fields: set[str] = set()
    for err in detail:
        loc = err.get("loc", [])
        if len(loc) >= 2 and loc[0] == "body":
            fields.add(str(loc[1]))
            continue
        msg = err.get("msg", "")
        msg = msg.split("Value error, ", 1)[-1]
        for part in msg.split("; "):
            name, sep, _ = part.partition(":")
            if sep:
                fields.add(name.strip())
    return fields


# ---------------------------------------------------------------------------
# Property 1
# ---------------------------------------------------------------------------

# Feature: adset-creative-diversity, Property 1: For any generated payload (add_variant in
# {true, false, null, omitted}, id_variant in {omitted, null, [], lists with ints >= 1 or with
# some value < 1, any length}, id_ad, id_adset and n_variants in ranges including 0 and
# negatives, project_id in {omitted, "", whitespace, text} and the Diversity_Flag True or
# False), the Variant_Endpoint and the Run_Local_Endpoint (DEBUG=True) accept the request iff a
# pure oracle encoding rules 1.2-1.8 accepts it; when rejecting they answer 422 naming each
# offending field and make 0 calls to apply_async and _run_phase1. A non-empty id_variant whose
# length differs from n_variants is never a rejection reason.
@hsettings(max_examples=100, deadline=None)
@given(fields=payload_fields, diversity_flag=st.booleans())
def test_property_1_variant_create_validation_matches_oracle(fields, diversity_flag):
    """**Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9**"""
    payload = build_payload(fields)
    expected = oracle_rejected_fields(payload, diversity_flag)

    for url, ok_status in ((VARIANTS_URL, 201), (RUN_LOCAL_URL, 200)):
        with variants_env(diversity_flag=diversity_flag) as env:
            resp = env.client.post(url, json=payload, headers=GOOD_HEADERS)
            ctx = f"{url} payload={payload} flag={diversity_flag}"
            if expected:
                assert resp.status_code == 422, f"{ctx}: {resp.status_code} {resp.text}"
                assert detail_fields(resp.json()["detail"]) == expected, f"{ctx}: {resp.text}"
                assert env.apply_async.call_count == 0, ctx
                assert env.phase1.call_count == 0, ctx
            else:
                assert resp.status_code == ok_status, f"{ctx}: {resp.status_code} {resp.text}"
                if url == VARIANTS_URL:
                    assert env.apply_async.call_count == 1, ctx
                    assert env.phase1.call_count == 0, ctx
                else:
                    assert env.phase1.call_count == 1, ctx
                    assert env.apply_async.call_count == 0, ctx


# ---------------------------------------------------------------------------
# Property 2
# ---------------------------------------------------------------------------

# Defaults of VariantCreate for the 7 propagated parameters (applied when omitted).
_MODEL_DEFAULTS = {
    "id_adset": 0, "n_variants": 3, "project_id": None, "id_ad": 0,
    "custom_prompt": None, "add_variant": True, "id_variant": None,
}

_SECRET_URL = "https://storage.example.com/img.png?X-Goog-Signature=deadbeef&X-Goog-Credential=svc"
_SECRET_KEY = "sk-live-SECRETKEY1234567890"


class CustomPipelineError(Exception):
    """Arbitrary user-defined exception class raised by the pipeline."""


_EXC_TYPES = (ValueError, RuntimeError, KeyError, TimeoutError, ConnectionError, CustomPipelineError)


@st.composite
def valid_payloads(draw: st.DrawFn, diversity_flag: bool) -> dict[str, Any]:
    """Payloads accepted by the oracle (Req 1), with optional keys randomly omitted."""
    fields: dict[str, Any] = {"id_adset": draw(st.integers(min_value=1, max_value=10_000))}
    add_variant = draw(st.sampled_from([True, False, None, OMIT]))
    replace = add_variant is False or add_variant is None
    if add_variant is not OMIT:
        fields["add_variant"] = add_variant

    n_variants = draw(_with_omit(st.integers(min_value=1, max_value=8)))
    if n_variants is not OMIT:
        fields["n_variants"] = n_variants

    if replace:
        fields["id_ad"] = draw(st.integers(min_value=1, max_value=10_000))
        fields["id_variant"] = draw(st.lists(st.integers(min_value=1, max_value=500), min_size=1, max_size=8))
    else:
        id_ad = draw(_with_omit(st.one_of(st.none(), st.integers(min_value=0, max_value=10_000))))
        if id_ad is not OMIT:
            fields["id_ad"] = id_ad
        id_variant = draw(_with_omit(st.one_of(
            st.none(), st.just([]),
            st.lists(st.integers(min_value=1, max_value=500), min_size=1, max_size=8),
        )))
        if id_variant is not OMIT:
            fields["id_variant"] = id_variant

    non_blank = st.text(alphabet="abcXYZ019-_ ", min_size=1, max_size=12).filter(lambda s: s.strip())
    if diversity_flag:
        fields["project_id"] = draw(non_blank)
    else:
        project_id = draw(_with_omit(st.one_of(st.none(), st.just(""), non_blank)))
        if project_id is not OMIT:
            fields["project_id"] = project_id

    custom_prompt = draw(_with_omit(st.one_of(st.none(), st.text(max_size=40))))
    if custom_prompt is not OMIT:
        fields["custom_prompt"] = custom_prompt
    return fields


@st.composite
def p2_cases(draw: st.DrawFn) -> tuple[dict[str, Any], bool, BaseException | None, dict[str, Any]]:
    diversity_flag = draw(st.booleans())
    payload = draw(valid_payloads(diversity_flag))
    error = draw(st.one_of(
        st.none(),
        st.builds(
            lambda cls, msg: cls(msg),
            st.sampled_from(_EXC_TYPES),
            st.sampled_from([
                f"download failed for {_SECRET_URL}",
                f"auth error api_key={_SECRET_KEY}",
                f"{_SECRET_URL} {_SECRET_KEY}",
                "",
            ]),
        ),
    ))
    result = draw(st.fixed_dictionaries({
        "ads": st.lists(st.fixed_dictionaries({"id": st.integers(min_value=1, max_value=999)}), max_size=3),
        "marker": st.text(alphabet="abc", max_size=5),
    }))
    return payload, diversity_flag, error, result


# Feature: adset-creative-diversity, Property 2: For any valid VariantCreate, create_variant calls
# apply_async exactly once with kwargs equal to the 7 request parameters (defaults applied) and
# answers 201 with the job envelope, and the Run_Local_Endpoint calls _run_phase1 exactly once with
# task=None, a fresh UUID4 task_id and those 7 parameters unmodified, answering 200 with
# {"ok": 1, "data": <result>}; and for any exception raised by _run_phase1 with any message
# (including signed URLs and keys), the response is 500 with detail == type(exc).__name__.
@hsettings(max_examples=100, deadline=None)
@given(case=p2_cases())
def test_property_2_param_propagation_and_sanitized_error(case):
    """**Validates: Requirements 10.1, 10.3, 10.5**"""
    payload, diversity_flag, error, result = case
    assert not oracle_rejected_fields(payload, diversity_flag), payload  # generator sanity
    expected = {k: payload.get(k, _MODEL_DEFAULTS[k]) for k in PIPELINE_PARAMS}
    ctx = f"payload={payload} flag={diversity_flag} error={error!r}"

    # Variant_Endpoint (Req 10.5)
    with variants_env(diversity_flag=diversity_flag) as env:
        resp = env.client.post(VARIANTS_URL, json=payload, headers=GOOD_HEADERS)
        assert resp.status_code == 201, f"{ctx}: {resp.status_code} {resp.text}"
        assert env.apply_async.call_count == 1, ctx
        assert env.phase1.call_count == 0, ctx
        assert env.apply_async.calls[0]["kwargs"] == {"kwargs": expected}, ctx
        task_id = env.apply_async.ids[0]
        assert resp.json() == {"ok": 1, "data": {
            "variant_job_id": task_id,
            "id_adset": expected["id_adset"],
            "n_variants": expected["n_variants"],
            "status": "RUNNING",
            "poll_url": f"/api/v2/jobs/{task_id}",
        }}, ctx

    # Run_Local_Endpoint (Req 10.1, 10.2, 10.3)
    with variants_env(diversity_flag=diversity_flag, phase1=Phase1Spy(result=result, error=error)) as env:
        resp = env.client.post(RUN_LOCAL_URL, json=payload, headers=GOOD_HEADERS)
        assert env.apply_async.call_count == 0, ctx
        assert env.phase1.call_count == 1, ctx
        call = env.phase1.calls[0]
        assert set(call) == {"task", "task_id", *PIPELINE_PARAMS}, ctx
        assert call["task"] is None, ctx
        assert uuid.UUID(call["task_id"]).version == 4, ctx
        assert str(uuid.UUID(call["task_id"])) == call["task_id"], ctx
        assert {k: call[k] for k in PIPELINE_PARAMS} == expected, ctx

        if error is None:
            assert resp.status_code == 200, f"{ctx}: {resp.status_code} {resp.text}"
            assert resp.json() == {"ok": 1, "data": result}, ctx
        else:
            assert resp.status_code == 500, f"{ctx}: {resp.status_code} {resp.text}"
            assert resp.json()["detail"] == type(error).__name__, f"{ctx}: {resp.text}"
            assert _SECRET_URL not in resp.text and "X-Goog-Signature" not in resp.text, ctx
            assert _SECRET_KEY not in resp.text, ctx


if __name__ == "__main__":
    import sys
    import traceback

    tests = [
        (name, obj) for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
