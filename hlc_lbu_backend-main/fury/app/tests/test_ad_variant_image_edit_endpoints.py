"""Unit tests for the ad-variant image-edit endpoints and the jobs.py result change.

Covers POST /api/v2/variants/image/edit, POST /api/v2/variants/image/edit/run-local
and GET /api/v2/jobs/{task_id} (Req 2, 3, 10.7, 13.14, 13.15, 13.20, 13.21).
Everything runs in memory: `apply_async`, the pipeline coroutine and
`celery_app.AsyncResult` are patched; no Redis, Celery, Sinergia or network.

Runnable two ways:
    python -m tests.test_ad_variant_image_edit_endpoints   # runs tests, prints summary
    pytest tests/test_ad_variant_image_edit_endpoints.py   # standard collection
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
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services import job_runner_service
from services.celery_app import celery_app
from tests._edit_pipeline_fakes import DEFAULT_INTERNAL_API_KEY, patched_pipeline

EDIT_URL = "/api/v2/variants/image/edit"
RUN_LOCAL_URL = "/api/v2/variants/image/edit/run-local"
JOBS_URL = "/api/v2/jobs"

GOOD_HEADERS = {"X-Internal-API-Key": DEFAULT_INTERNAL_API_KEY}
BAD_HEADERS = {"X-Internal-API-Key": "definitely-not-the-right-key"}

REQUIRED_FIELDS = (
    "brand_id", "campaign_id", "ad_id", "channel_id", "variant_id",
    "image_name", "id_base_image", "n_variations",
)
ALL_FIELDS = REQUIRED_FIELDS + ("custom_prompt", "expand_zoom_option")
INT_ID_FIELDS = ("brand_id", "campaign_id", "ad_id", "channel_id", "variant_id")


def valid_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "brand_id": 1,
        "campaign_id": 2,
        "ad_id": 3,
        "channel_id": 4,
        "variant_id": 5,
        "image_name": "summer_sale",
        "id_base_image": "img_abc",
        "n_variations": 2,
        "custom_prompt": "Add a sunset sky",
        "expand_zoom_option": "TOP",
    }
    payload.update(overrides)
    return payload


def invalid_payloads() -> list[tuple[str, dict[str, Any]]]:
    """Every invalid payload listed in Req 13.14."""
    cases: list[tuple[str, dict[str, Any]]] = [
        ("n_variations=0", valid_payload(n_variations=0)),
        ("n_variations=11", valid_payload(n_variations=11)),
        ("custom_prompt=None", valid_payload(custom_prompt=None, expand_zoom_option=None)),
        ("custom_prompt=''", valid_payload(custom_prompt="", expand_zoom_option=None)),
        ("custom_prompt='   '", valid_payload(custom_prompt="   ", expand_zoom_option=None)),
        ("expand_zoom_option='top'", valid_payload(expand_zoom_option="top")),
        ("expand_zoom_option='ZOOM_3X'", valid_payload(expand_zoom_option="ZOOM_3X")),
        ("brand_id='abc'", valid_payload(brand_id="abc")),
        ("image_name=''", valid_payload(image_name="")),
        ("id_base_image=''", valid_payload(id_base_image="")),
    ]
    for field in REQUIRED_FIELDS:
        payload = valid_payload()
        del payload[field]
        cases.append((f"missing {field}", payload))
    for field in INT_ID_FIELDS:
        cases.append((f"{field}=0", valid_payload(**{field: 0})))
    return cases


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeApplyAsync:
    """Records `apply_async` calls; returns an AsyncResult-like with a fresh id."""

    def __init__(self, error: BaseException | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error = error
        self.ids: list[str] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def __call__(self, *args: Any, **kwargs: Any) -> SimpleNamespace:
        self.calls.append({"args": args, "kwargs": copy.deepcopy(kwargs)})
        if self.error is not None:
            raise self.error
        task_id = str(uuid.uuid4())
        self.ids.append(task_id)
        return SimpleNamespace(id=task_id)


class PipelineSpy:
    """Stand-in for `_run_edit_ad_variant_image_pipeline` that records calls.

    With `delegate` set, the call is forwarded to that coroutine function.
    """

    def __init__(self, delegate: Any = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.delegate = delegate

    @property
    def call_count(self) -> int:
        return len(self.calls)

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(dict(kwargs))
        if self.delegate is not None:
            return await self.delegate(**kwargs)
        return {"never": "used"}


@contextmanager
def endpoint_env(
    *,
    debug: bool = False,
    internal_api_key: str | None = DEFAULT_INTERNAL_API_KEY,
    apply_async: FakeApplyAsync | None = None,
    pipeline: PipelineSpy | None = None,
) -> Iterator[SimpleNamespace]:
    """Patch settings, `apply_async` and the pipeline coroutine for one test."""
    env = SimpleNamespace(
        apply_async=apply_async or FakeApplyAsync(),
        pipeline=pipeline or PipelineSpy(),
        harness=None,
    )
    with ExitStack() as stack:
        env.harness = stack.enter_context(
            patched_pipeline(debug=debug, internal_api_key=internal_api_key)
        )
        stack.enter_context(
            patch.object(
                job_runner_service.run_edit_ad_variant_image_pipeline,
                "apply_async",
                env.apply_async,
            )
        )
        stack.enter_context(
            patch.object(job_runner_service, "_run_edit_ad_variant_image_pipeline", env.pipeline)
        )
        env.client = TestClient(app, raise_server_exceptions=False)
        yield env


# ---------------------------------------------------------------------------
# POST /variants/image/edit
# ---------------------------------------------------------------------------


def test_edit_valid_request_returns_201_and_enqueues_once_with_all_fields():
    """Req 2.1, 2.2, 2.6, 13.20."""
    with endpoint_env() as env:
        resp = env.client.post(EDIT_URL, json=valid_payload(), headers=GOOD_HEADERS)

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["ok"] == 1
        data = body["data"]
        assert data["status"] == "RUNNING"
        assert isinstance(data["edit_job_id"], str) and data["edit_job_id"]
        assert data["poll_url"] == f"/api/v2/jobs/{data['edit_job_id']}"
        assert data["edit_job_id"] == env.apply_async.ids[0]

        assert env.apply_async.call_count == 1
        call = env.apply_async.calls[0]
        assert call["args"] == ()
        assert call["kwargs"]["kwargs"] == valid_payload()
        assert set(call["kwargs"]["kwargs"]) == set(ALL_FIELDS)
        # Nothing of the pipeline runs inside the request (2.6).
        assert env.pipeline.call_count == 0
        assert env.harness.get_ad_variant_image.call_count == 0
        assert env.harness.edit.call_count == 0
        assert env.harness.run_agent.call_count == 0
        assert env.harness.upload.call_count == 0


def test_edit_enqueues_none_fields_and_enum_as_str():
    """Req 2.1: None fields are included; expand_zoom_option serialized as str."""
    with endpoint_env() as env:
        payload = valid_payload(custom_prompt=None, expand_zoom_option="ZOOM_1_5X")
        resp = env.client.post(EDIT_URL, json=payload, headers=GOOD_HEADERS)

        assert resp.status_code == 201, resp.text
        kwargs = env.apply_async.calls[0]["kwargs"]["kwargs"]
        assert set(kwargs) == set(ALL_FIELDS)
        assert kwargs["custom_prompt"] is None
        assert kwargs["expand_zoom_option"] == "ZOOM_1_5X"
        assert type(kwargs["expand_zoom_option"]) is str

        payload = valid_payload(expand_zoom_option=None)
        resp = env.client.post(EDIT_URL, json=payload, headers=GOOD_HEADERS)
        assert resp.status_code == 201, resp.text
        kwargs = env.apply_async.calls[1]["kwargs"]["kwargs"]
        assert set(kwargs) == set(ALL_FIELDS)
        assert kwargs["expand_zoom_option"] is None


def test_edit_invalid_payloads_return_422_without_enqueue():
    """Req 1.3–1.7, 1.10, 13.14."""
    with endpoint_env() as env:
        for label, payload in invalid_payloads():
            resp = env.client.post(EDIT_URL, json=payload, headers=GOOD_HEADERS)
            assert resp.status_code == 422, (label, resp.status_code, resp.text)
        assert env.apply_async.call_count == 0
        assert env.pipeline.call_count == 0


def test_edit_returns_503_when_internal_api_key_not_configured():
    """Req 2.4."""
    for configured in ("", None):
        with endpoint_env(internal_api_key=configured) as env:
            resp = env.client.post(EDIT_URL, json=valid_payload(), headers=GOOD_HEADERS)
            assert resp.status_code == 503, (configured, resp.text)
            assert env.apply_async.call_count == 0


def test_edit_apply_async_failure_returns_5xx_without_job_fields():
    """Req 2.5."""
    with endpoint_env(apply_async=FakeApplyAsync(error=ConnectionError("broker down"))) as env:
        resp = env.client.post(EDIT_URL, json=valid_payload(), headers=GOOD_HEADERS)

        assert 500 <= resp.status_code <= 599, resp.text
        assert env.apply_async.call_count == 1
        assert "edit_job_id" not in resp.text
        assert "poll_url" not in resp.text
        body = resp.json()
        assert body["ok"] == 0
        assert "encolar" in body["message"]["text"]


def test_edit_two_identical_requests_get_distinct_job_ids():
    """Req 2.7."""
    with endpoint_env() as env:
        first = env.client.post(EDIT_URL, json=valid_payload(), headers=GOOD_HEADERS)
        second = env.client.post(EDIT_URL, json=valid_payload(), headers=GOOD_HEADERS)

        assert first.status_code == second.status_code == 201
        id1 = first.json()["data"]["edit_job_id"]
        id2 = second.json()["data"]["edit_job_id"]
        assert id1 != id2
        assert env.apply_async.call_count == 2


# ---------------------------------------------------------------------------
# Auth (both endpoints)
# ---------------------------------------------------------------------------


def test_missing_or_invalid_key_rejected_without_enqueue_or_pipeline():
    """Req 2.3, 3.2, 13.21 — auth precedes 422 and is independent of DEBUG."""
    for debug in (False, True):
        with endpoint_env(debug=debug) as env:
            for url in (EDIT_URL, RUN_LOCAL_URL):
                for payload in (valid_payload(), valid_payload(n_variations=0)):
                    resp = env.client.post(url, json=payload)
                    assert resp.status_code in {401, 403}, (debug, url, resp.text)

                    resp = env.client.post(url, json=payload, headers=BAD_HEADERS)
                    assert resp.status_code == 401, (debug, url, resp.text)

            assert env.apply_async.call_count == 0
            assert env.pipeline.call_count == 0


# ---------------------------------------------------------------------------
# POST /variants/image/edit/run-local
# ---------------------------------------------------------------------------


def test_run_local_returns_404_when_debug_false():
    """Req 3.3, 13.15."""
    with endpoint_env(debug=False) as env:
        resp = env.client.post(RUN_LOCAL_URL, json=valid_payload(), headers=GOOD_HEADERS)

        assert resp.status_code == 404, resp.text
        assert env.pipeline.call_count == 0
        assert env.apply_async.call_count == 0


def test_run_local_invalid_payload_returns_422_without_pipeline():
    """Req 3.4."""
    with endpoint_env(debug=True) as env:
        for label, payload in invalid_payloads():
            resp = env.client.post(RUN_LOCAL_URL, json=payload, headers=GOOD_HEADERS)
            assert resp.status_code == 422, (label, resp.status_code, resp.text)
        assert env.pipeline.call_count == 0
        assert env.apply_async.call_count == 0


def test_run_local_debug_true_runs_pipeline_inline_and_returns_result():
    """Req 3.5, 3.6: inline run with task=None and a fresh UUID task_id per request."""
    real_pipeline = job_runner_service._run_edit_ad_variant_image_pipeline
    spy = PipelineSpy(delegate=real_pipeline)
    with endpoint_env(debug=True, pipeline=spy) as env:
        payload = valid_payload(n_variations=2)
        first = env.client.post(RUN_LOCAL_URL, json=payload, headers=GOOD_HEADERS)
        second = env.client.post(RUN_LOCAL_URL, json=payload, headers=GOOD_HEADERS)

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert env.apply_async.call_count == 0
        assert spy.call_count == 2

        for resp, call in zip((first, second), spy.calls):
            assert call["task"] is None
            task_id = call["task_id"]
            assert str(uuid.UUID(task_id)) == task_id
            assert {k: call[k] for k in ALL_FIELDS} == payload

            body = resp.json()
            assert body["ok"] == 1
            data = body["data"]
            assert set(data) == {"task_id", "variant_id", "id_base_image", "status", "variations"}
            assert data["task_id"] == task_id
            assert data["variant_id"] == payload["variant_id"]
            assert data["id_base_image"] == payload["id_base_image"]
            assert data["status"] == "DONE"
            assert 1 <= len(data["variations"]) <= payload["n_variations"]
            for variation in data["variations"]:
                assert set(variation) == {"id", "url", "prompt"}
                assert all(isinstance(v, str) and v for v in variation.values())

        assert spy.calls[0]["task_id"] != spy.calls[1]["task_id"]


# ---------------------------------------------------------------------------
# GET /jobs/{task_id}
# ---------------------------------------------------------------------------


def _poll_success(info: Any) -> dict[str, Any]:
    fake_result = SimpleNamespace(state="SUCCESS", info=info)
    with endpoint_env() as env, patch.object(celery_app, "AsyncResult", lambda _id: fake_result):
        resp = env.client.get(f"{JOBS_URL}/some-task-id", headers=GOOD_HEADERS)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_jobs_returns_full_result_for_edit_pipeline():
    """Req 10.7: full result only for this pipeline."""
    result = {
        "task_id": "some-task-id",
        "variant_id": 5,
        "id_base_image": "img_abc",
        "status": "DONE",
        "variations": [
            {"id": "img_1", "url": "https://fake-sinergia.local/1.png", "prompt": "A sunset"},
        ],
    }
    body = _poll_success(copy.deepcopy(result))
    assert body["ok"] == 1
    assert body["data"]["status"] == "DONE"
    assert body["data"]["result"] == result


def test_jobs_returns_ok_for_other_pipelines():
    """Req 10.7: other pipelines keep returning "Ok"."""
    others = (
        {"proposals": [], "renders": []},
        {"task_id": "x", "status": "DONE"},
        {"task_id": "x", "variant_id": 1, "id_base_image": "a", "status": "DONE",
         "variations": [], "extra": 1},
        {},
    )
    for info in others:
        body = _poll_success(info)
        assert body["ok"] == 1
        assert body["data"]["result"] == "Ok", info


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

from hypothesis import assume, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from schemas.pipeline_schemas import AdVariantImageEditCreate, ExpandZoomOption  # noqa: E402

_ids = st.integers(min_value=1, max_value=2**31 - 1)
_padding = st.sampled_from(["", " ", "  ", "\t", "\n "])
_core_text = st.text(min_size=1, max_size=40).filter(lambda s: s.strip())


@st.composite
def _padded(draw: Any, core: Any = _core_text) -> str:
    return draw(_padding) + draw(core) + draw(_padding)


@st.composite
def _valid_edit_requests(draw: Any) -> dict[str, Any]:
    """Raw JSON bodies that `AdVariantImageEditCreate` accepts (incl. padding/normalisation)."""
    option = draw(st.one_of(st.none(), st.sampled_from([o.value for o in ExpandZoomOption])))
    prompt_choices = [_padded()]
    if option is not None:
        # Absent / null / blank prompts are only valid when an option is given.
        prompt_choices += [st.none(), st.sampled_from(["", "   "])]
    payload: dict[str, Any] = {
        **{field: draw(_ids) for field in INT_ID_FIELDS},
        "image_name": draw(_padded()),
        "id_base_image": draw(_padded()),
        "n_variations": draw(st.integers(min_value=1, max_value=10)),
        "custom_prompt": draw(st.one_of(*prompt_choices)),
        "expand_zoom_option": option,
    }
    # Optional fields may also be omitted from the body entirely.
    for optional in ("custom_prompt", "expand_zoom_option"):
        if payload[optional] is None and draw(st.booleans()):
            del payload[optional]
    return payload


class _RandomIdApplyAsync(FakeApplyAsync):
    """FakeApplyAsync whose returned task id is supplied by Hypothesis."""

    def __init__(self, task_id: str) -> None:
        super().__init__()
        self._task_id = task_id

    def __call__(self, *args: Any, **kwargs: Any) -> SimpleNamespace:
        self.calls.append({"args": args, "kwargs": copy.deepcopy(kwargs)})
        self.ids.append(self._task_id)
        return SimpleNamespace(id=self._task_id)


# Feature: ad-variant-image-edit-pipeline, Property 4: El encolado preserva el request
@settings(max_examples=100, deadline=None)
@given(
    payload=_valid_edit_requests(),
    task_id=st.one_of(
        st.uuids().map(str),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=40),
    ),
)
def test_property_enqueue_preserves_request(payload: dict[str, Any], task_id: str):
    """**Validates: Requirements 1.1, 2.1, 2.2, 13.20**"""
    try:
        expected = AdVariantImageEditCreate(**payload).model_dump(mode="json")
    except ValidationError:
        assume(False)
        raise  # unreachable

    with endpoint_env(apply_async=_RandomIdApplyAsync(task_id)) as env:
        resp = env.client.post(EDIT_URL, json=payload, headers=GOOD_HEADERS)

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["ok"] == 1
        assert body["data"] == {
            "edit_job_id": task_id,
            "status": "RUNNING",
            "poll_url": f"/api/v2/jobs/{task_id}",
        }

        assert env.apply_async.call_count == 1
        enqueued = env.apply_async.calls[0]["kwargs"]["kwargs"]
        assert enqueued == expected
        assert set(enqueued) == set(ALL_FIELDS) and len(enqueued) == 10
        option = enqueued["expand_zoom_option"]
        assert option is None or type(option) is str
        assert env.pipeline.call_count == 0


_json_scalars = st.one_of(
    st.none(), st.booleans(), st.integers(), st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=20),
)
_arbitrary_json = st.recursive(
    _json_scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(max_size=10), children, max_size=4),
    ),
    max_leaves=10,
)
# Header-safe wrong keys (non-empty, no surrounding whitespace) distinct from the real one.
_wrong_keys = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
    min_size=1, max_size=60,
).filter(lambda k: k != DEFAULT_INTERNAL_API_KEY)


# Feature: ad-variant-image-edit-pipeline, Property 5: La autenticación precede a todo
@settings(max_examples=100, deadline=None)
@given(
    body=st.one_of(_valid_edit_requests(), _arbitrary_json),
    debug=st.booleans(),
    url=st.sampled_from([EDIT_URL, RUN_LOCAL_URL]),
    wrong_key=st.one_of(st.none(), _wrong_keys),
)
def test_property_auth_precedes_everything(
    body: Any, debug: bool, url: str, wrong_key: str | None
):
    """**Validates: Requirements 2.3, 3.2, 13.21**"""
    with endpoint_env(debug=debug) as env:
        if wrong_key is None:
            resp = env.client.post(url, json=body)
            assert resp.status_code in {401, 403}, (debug, url, resp.status_code, resp.text)
        else:
            resp = env.client.post(url, json=body, headers={"X-Internal-API-Key": wrong_key})
            assert resp.status_code == 401, (debug, url, resp.status_code, resp.text)

        assert env.apply_async.call_count == 0
        assert env.pipeline.call_count == 0


from core import exceptions as fury_exceptions  # noqa: E402

# Every concrete FuryException subclass defined in core.exceptions (incl. the base).
_FURY_EXC_CLASSES = sorted(
    (
        obj for obj in vars(fury_exceptions).values()
        if isinstance(obj, type) and issubclass(obj, fury_exceptions.FuryException)
    ),
    key=lambda cls: cls.__name__,
)
_json_details = st.dictionaries(st.text(max_size=10), _arbitrary_json, max_size=4)


class _CustomPipelineCrash(Exception):
    """A non-Fury exception type unknown to the endpoint."""


_NON_FURY_EXC_TYPES = (
    ValueError, RuntimeError, KeyError, TypeError, ConnectionError, TimeoutError,
    OSError, _CustomPipelineCrash,
)


@st.composite
def _fury_exceptions(draw: Any) -> fury_exceptions.FuryException:
    cls = draw(st.sampled_from(_FURY_EXC_CLASSES))
    message = draw(st.text(max_size=80))
    details = draw(st.one_of(st.none(), _json_details))
    if cls is fury_exceptions.FuryException:
        return cls(
            message=message,
            code=draw(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_", min_size=1, max_size=30)),
            status_code=draw(st.integers(min_value=400, max_value=599)),
            details=details,
        )
    return cls(message, details=details)


@st.composite
def _sensitive_messages(draw: Any) -> tuple[str, list[str]]:
    """A non-Fury error message embedding signed URLs, data-URIs and keys.

    Returns (message, secrets) where every secret must not leak into the response.
    """
    token = "SECRET" + draw(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                min_size=12, max_size=32)
    )
    signed_url = (
        f"https://bucket.s3.amazonaws.com/img.png?X-Amz-Credential={token}cred"
        f"&X-Amz-Security-Token={token}sess&X-Amz-Signature={token}sig"
    )
    data_uri = f"data:image/png;base64,{token}b64payload=="
    api_key = f"{token}apikey"
    parts = draw(st.lists(st.sampled_from([signed_url, data_uri, api_key]), min_size=1, max_size=3))
    filler = draw(st.text(max_size=30))
    message = filler + " " + " ".join(parts)
    secrets = [token, "X-Amz-Credential", "X-Amz-Security-Token", "X-Amz-Signature", ";base64,"]
    return message, secrets


def _raising_pipeline(exc: BaseException) -> PipelineSpy:
    async def _raise(**_kwargs: Any) -> Any:
        raise exc

    return PipelineSpy(delegate=_raise)


# Feature: ad-variant-image-edit-pipeline, Property 17: Mapeo de errores del Run_Local_Endpoint
@settings(max_examples=100, deadline=None)
@given(
    payload=_valid_edit_requests(),
    fury_exc=st.one_of(st.none(), _fury_exceptions()),
    non_fury_type=st.sampled_from(_NON_FURY_EXC_TYPES),
    sensitive=_sensitive_messages(),
)
def test_property_run_local_error_mapping(
    payload: dict[str, Any],
    fury_exc: fury_exceptions.FuryException | None,
    non_fury_type: type[Exception],
    sensitive: tuple[str, list[str]],
):
    """**Validates: Requirements 3.7, 12.2, 12.3**"""
    try:
        AdVariantImageEditCreate(**payload)
    except ValidationError:
        assume(False)

    if fury_exc is not None:
        with endpoint_env(debug=True, pipeline=_raising_pipeline(fury_exc)) as env:
            resp = env.client.post(RUN_LOCAL_URL, json=payload, headers=GOOD_HEADERS)

            assert env.pipeline.call_count == 1  # no retry (3.7)
            assert env.apply_async.call_count == 0
            assert resp.status_code == fury_exc.status_code, resp.text
            assert resp.json() == {
                "ok": 0,
                "message": {"code": fury_exc.code, "text": fury_exc.message},
                "details": fury_exc.details,
            }
        return

    message, secrets = sensitive
    exc = non_fury_type(message)
    with endpoint_env(debug=True, pipeline=_raising_pipeline(exc)) as env:
        resp = env.client.post(RUN_LOCAL_URL, json=payload, headers=GOOD_HEADERS)

        assert env.pipeline.call_count == 1  # no retry (3.7)
        assert env.apply_async.call_count == 0
        task_id = env.pipeline.calls[0]["task_id"]

        assert resp.status_code == 500, resp.text
        body = resp.json()
        assert set(body) == {"ok", "message", "details"}
        assert body["ok"] == 0
        assert body["message"]["code"] == "INTERNAL_ERROR"
        assert isinstance(body["message"]["text"], str) and body["message"]["text"]
        assert body["details"] == {"task_id": task_id, "error_type": non_fury_type.__name__}

        for secret in secrets:
            assert secret not in resp.text, (secret, resp.text)
        assert message.strip() not in resp.text
        assert "Traceback" not in resp.text


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ad-variant image-edit endpoint tests passed")
