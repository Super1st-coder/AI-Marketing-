"""Tests for the ad-variant image-edit Celery task and its exceptions.

Runnable two ways:
    python -m tests.test_ad_variant_image_edit_task   # runs tests, prints summary
    pytest tests/test_ad_variant_image_edit_task.py   # standard collection
"""
from __future__ import annotations

import asyncio
import pickle
import string
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

import services.job_runner_service as jrs
from core.logging import logger as _loguru_logger

from core.exceptions import (
    AdVariantImageEditError,
    BaseImageDownloadError,
    BaseImageFetchError,
    BaseImageMismatchError,
    BaseImageUrlMissingError,
    EditJobEnqueueError,
    EditPipelineInternalError,
    ImageEditingFailedError,
    VariationUploadFailedError,
    VariationUrlResolutionError,
)

EDIT_ERROR_CLASSES = [
    AdVariantImageEditError,
    BaseImageFetchError,
    BaseImageMismatchError,
    BaseImageUrlMissingError,
    BaseImageDownloadError,
    ImageEditingFailedError,
    VariationUploadFailedError,
    VariationUrlResolutionError,
    EditJobEnqueueError,
    EditPipelineInternalError,
]

# JSON-compatible values (no NaN: NaN != NaN would break equality checks).
_json_scalars = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-(2**53), max_value=2**53)
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=30)
)
_json_values = st.recursive(
    _json_scalars,
    lambda children: st.lists(children, max_size=4)
    | st.dictionaries(st.text(max_size=10), children, max_size=4),
    max_leaves=10,
)
_json_details = st.dictionaries(st.text(max_size=15), _json_values, max_size=5)


# Feature: ad-variant-image-edit-pipeline, Property 16: Round-trip de pickle de las excepciones
@settings(max_examples=100, deadline=None)
@given(
    cls=st.sampled_from(EDIT_ERROR_CLASSES),
    message=st.text(max_size=100),
    details=_json_details | st.none(),
)
def test_property_16_exception_pickle_round_trip(cls, message, details):
    """**Validates: Requirements 12.8**"""
    e = cls(message, details)

    restored = pickle.loads(pickle.dumps(e))
    assert type(restored) is cls
    assert restored.message == e.message == message
    assert restored.code == e.code == cls.code
    assert restored.status_code == e.status_code == cls.status_code
    assert restored.details == e.details == (details or {})

    # Celery JSON backend reconstructs exceptions as ``cls(*args)``.
    rebuilt = type(e)(*e.args)
    assert type(rebuilt) is cls
    assert rebuilt.message == message


# --- Unit tests: exceptions table (design §9) ------------------------------

# (class, code, status_code, step, retryable). retryable=None means "n/a" in the
# design table (not raised inside the Celery retry loop), so it is not asserted.
EXPECTED_EXCEPTION_TABLE = [
    (BaseImageFetchError, "AD_VARIANT_BASE_IMAGE_FETCH_FAILED", 502, "fetch_base_image", True),
    (BaseImageMismatchError, "AD_VARIANT_BASE_IMAGE_ID_MISMATCH", 409, "fetch_base_image", False),
    (BaseImageUrlMissingError, "AD_VARIANT_BASE_IMAGE_URL_MISSING", 422, "download", False),
    (BaseImageDownloadError, "AD_VARIANT_BASE_IMAGE_DOWNLOAD_FAILED", 502, "download", True),
    (ImageEditingFailedError, "AD_VARIANT_IMAGE_EDITING_FAILED", 502, "image_editing", True),
    (VariationUploadFailedError, "AD_VARIANT_IMAGE_UPLOAD_FAILED", 502, "upload", True),
    (
        VariationUrlResolutionError,
        "AD_VARIANT_IMAGE_URL_RESOLUTION_FAILED",
        502,
        "resolve_urls",
        True,
    ),
    (EditJobEnqueueError, "AD_VARIANT_IMAGE_EDIT_ENQUEUE_FAILED", 503, "enqueue", None),
    (EditPipelineInternalError, "INTERNAL_ERROR", 500, "", None),
]


def test_exception_codes_unique_and_non_empty():
    """Requirements 12.1"""
    codes = [cls.code for cls in EDIT_ERROR_CLASSES]
    assert all(isinstance(c, str) and c.strip() for c in codes)
    assert len(codes) == len(set(codes))


def test_exception_status_codes_in_error_range():
    """Requirements 12.1"""
    for cls in EDIT_ERROR_CLASSES:
        assert isinstance(cls.status_code, int)
        assert 400 <= cls.status_code <= 599, cls


def test_exception_table_matches_design():
    """Requirements 11.5, 12.1"""
    for cls, code, status, step, retryable in EXPECTED_EXCEPTION_TABLE:
        assert issubclass(cls, AdVariantImageEditError)
        assert cls.code == code, cls
        assert cls.status_code == status, cls
        assert cls.step == step, cls
        if retryable is not None:
            assert cls.retryable is retryable, cls
        # Instances expose the class-level attributes.
        e = cls("boom", {"task_id": "t"})
        assert (e.code, e.status_code, e.step) == (code, status, step)
        assert e.details == {"task_id": "t"}


def test_url_resolution_error_is_upload_failed_subclass():
    """Requirements 11.4, 14.7"""
    assert issubclass(VariationUrlResolutionError, VariationUploadFailedError)
    assert VariationUrlResolutionError.code != VariationUploadFailedError.code
    e = VariationUrlResolutionError("boom")
    assert isinstance(e, VariationUploadFailedError)
    assert e.retryable is True


def test_non_retryable_errors_are_exactly_mismatch_and_url_missing():
    """Requirements 11.5"""
    pipeline_classes = [row[0] for row in EXPECTED_EXCEPTION_TABLE if row[4] is not None]
    non_retryable = {cls for cls in pipeline_classes if not cls.retryable}
    assert non_retryable == {BaseImageMismatchError, BaseImageUrlMissingError}


# --- Celery task: decorator and retry policy (design §10, D7) ---------------

_EDIT_TASK_NAME = "services.job_runner_service.run_edit_ad_variant_image_pipeline"


def _edit_task():
    """Concrete task instance behind the Celery PromiseProxy."""
    task = jrs.run_edit_ad_variant_image_pipeline
    return getattr(task, "_get_current_object", lambda: task)()


class _RetrySignal(Exception):
    """Raised by the fake ``self.retry`` (stands in for ``celery.exceptions.Retry``)."""


_RETRYABLE_EDIT_CLASSES = [
    c for c in EDIT_ERROR_CLASSES if c is not AdVariantImageEditError and c.retryable
]
_NON_RETRYABLE_EDIT_CLASSES = [c for c in EDIT_ERROR_CLASSES if not c.retryable]
_GENERIC_CLASSES = [Exception, RuntimeError, ValueError, KeyError, TimeoutError]

# Messages that `_redact_text` leaves untouched, so the log can be checked verbatim.
_safe_message = st.text(alphabet=string.ascii_letters + string.digits + " _-", min_size=1, max_size=40)


@st.composite
def _pipeline_exceptions(draw):
    cls = draw(st.sampled_from(_RETRYABLE_EDIT_CLASSES + _NON_RETRYABLE_EDIT_CLASSES + _GENERIC_CLASSES))
    message = draw(_safe_message)
    if issubclass(cls, AdVariantImageEditError):
        return cls(message, {"task_id": "t", "step": cls.step})
    return cls(message)


_task_kwargs = st.fixed_dictionaries({
    "brand_id": st.integers(1, 10_000),
    "campaign_id": st.integers(1, 10_000),
    "ad_id": st.integers(1, 10_000),
    "channel_id": st.integers(1, 10),
    "variant_id": st.integers(1, 10_000),
    "image_name": st.text(alphabet=string.ascii_letters, min_size=1, max_size=12),
    "id_base_image": st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=12),
    "n_variations": st.integers(1, 4),
    "custom_prompt": st.none() | _safe_message,
    "expand_zoom_option": st.none() | st.sampled_from(["zoom_in", "zoom_out", "expand"]),
})


# Feature: ad-variant-image-edit-pipeline, Property 15: Política de reintentos de la tarea
@settings(max_examples=100, deadline=None)
@given(
    exc=_pipeline_exceptions(),
    retries=st.integers(0, 3),
    kwargs=_task_kwargs,
    task_id=st.uuids().map(str),
)
def test_property_15_task_retry_policy(exc, retries, kwargs, task_id):
    """**Validates: Requirements 4.4, 5.4, 7.9, 9.8, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6**"""
    task = _edit_task()
    events: list[tuple] = []
    loops: list[asyncio.AbstractEventLoop] = []
    log_lines: list[str] = []

    async def fake_pipeline(task_arg, tid, **fields):
        loops.append(asyncio.get_running_loop())
        events.append(("pipeline", task_arg, tid, fields))
        raise exc

    def fake_update_state(*args, **kw):
        events.append(("update_state", args, kw))

    def fake_retry(*args, **kw):
        events.append(("retry", args, kw))
        raise _RetrySignal()

    sink_id = _loguru_logger.add(lambda m: log_lines.append(str(m)), format="{message}", level="DEBUG")
    task.push_request(id=task_id, retries=retries)
    raised: BaseException | None = None
    try:
        with patch.object(jrs, "_run_edit_ad_variant_image_pipeline", fake_pipeline), \
             patch.object(task, "update_state", fake_update_state), \
             patch.object(task, "retry", fake_retry):
            try:
                task.run(**kwargs)
            except BaseException as e:  # noqa: BLE001 - asserting on what the task raises
                raised = e
    finally:
        task.pop_request()
        _loguru_logger.remove(sink_id)

    # 11.2: PROGRESS "starting" emitted first, before the pipeline runs.
    assert events[0] == ("update_state", (), {
        "state": "PROGRESS",
        "meta": {"step": "starting", "variant_id": kwargs["variant_id"],
                 "id_base_image": kwargs["id_base_image"]},
    })
    # The coroutine received the task, the same task_id and all fields.
    assert events[1][0] == "pipeline"
    assert events[1][1] is task
    assert events[1][2] == task_id
    assert events[1][3] == kwargs

    # 11.3: fresh loop per attempt, closed afterwards.
    assert len(loops) == 1 and loops[0].is_closed()

    retry_calls = [e for e in events if e[0] == "retry"]
    if not jrs._is_retryable_edit_error(exc):
        # 11.5: non-retryable → fail immediately with the same exception.
        assert raised is exc
        assert retry_calls == []
    elif retries < 3:
        # 11.4: retry once with exponential backoff.
        assert isinstance(raised, _RetrySignal)
        assert retry_calls == [("retry", (), {"exc": exc, "countdown": 2 ** retries})]
    else:
        # 11.6 / D7: retries exhausted → log type + original message and re-raise.
        assert raised is exc
        assert retry_calls == []
        assert any(
            f"[{task_id}]" in line and type(exc).__name__ in line and str(exc) in line
            for line in log_lines
        ), log_lines


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ad-variant image-edit task tests passed")
