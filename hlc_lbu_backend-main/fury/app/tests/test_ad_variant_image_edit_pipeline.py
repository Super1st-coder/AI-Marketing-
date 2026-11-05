"""Scenario tests for the ad-variant image-edit pipeline coroutine.

Covers Req 13.3, 13.5, 13.6, 13.7, 13.8, 13.9, 13.11, 13.12, 13.13, 13.16,
13.23, 13.24, 13.25, 13.26, 13.27, 13.28, 13.30 and 13.32 against `services.job_runner_service._run_edit_ad_variant_image_pipeline`.

Run:  PYTHONPATH=. env/bin/python -m pytest tests/test_ad_variant_image_edit_pipeline.py
  or: PYTHONPATH=. env/bin/python -m tests.test_ad_variant_image_edit_pipeline

Everything runs in memory (FakeRedis + scripted fakes of
`tests/_edit_pipeline_fakes.py`, incl. FakeSleep for Edit_Sleep);
`network_guard()` turns any real outbound
call into a failure (Req 13.1, 13.2).
"""
from __future__ import annotations

import asyncio
import mimetypes
from typing import Any

import httpx

from core.exceptions import (
    BaseImageDownloadError,
    BaseImageUrlMissingError,
    FuryException,
    ImageEditingFailedError,
    VariationUploadFailedError,
    VariationUrlResolutionError,
)
from services import job_runner_service as jrs
from services.edit_instruction import translate_expand_zoom_option
from tests._edit_pipeline_fakes import (
    DEFAULT,
    FakeDownloadBaseImage,
    FakeEditImageVariations,
    FakeGetAdVariantImage,
    FakeRedis,
    FakeRunAgent,
    FakeSleep,
    FakeTask,
    FakeUploadImageToLibrary,
    cp_key,
    make_variations,
    patched_pipeline,
    signed_url,
)

# Real download helper, captured before patched_pipeline swaps it for a fake.
_REAL_DOWNLOAD = jrs._download_base_image

_TASK_ID = "scenario-task-id"
_AD_ID = 3
_ID_BASE_IMAGE = "base-img-123"
_CUSTOM_PROMPT = "Make the background a sunny beach"
_PROGRESS_ORDER = [
    "fetch_base_image", "download", "image_editing", "prompt_analysis", "upload",
    "resolve_urls", "done",
]
_LIBRARY_INDEX_DELAY_S = 15
_RESOLVE_URL_RETRY_DELAY_S = 5


def _kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = dict(
        brand_id=1,
        campaign_id=2,
        ad_id=_AD_ID,
        channel_id=4,
        variant_id=5,
        image_name="banner.png",
        id_base_image=_ID_BASE_IMAGE,
        n_variations=3,
        custom_prompt=_CUSTOM_PROMPT,
        expand_zoom_option=None,
    )
    base.update(overrides)
    return base


def _run(task: Any = None, **overrides: Any) -> dict[str, Any]:
    return asyncio.run(
        jrs._run_edit_ad_variant_image_pipeline(task, _TASK_ID, **_kwargs(**overrides))
    )


def _run_expect(exc_type: type[BaseException], task: Any = None, **overrides: Any) -> BaseException:
    try:
        _run(task, **overrides)
    except exc_type as exc:
        return exc
    raise AssertionError(f"expected {exc_type.__name__} to be raised")


def _analyzed(indices: list[int]) -> list[dict[str, Any]]:
    return [
        {**v, "prompt": f"checkpoint prompt {v['index']}", "prompt_source": "agent"}
        for v in make_variations(indices)
    ]


def _seed_until_analysis(redis: FakeRedis, indices: list[int]) -> None:
    """Checkpoints of every step before `upload` (as left by a previous attempt)."""
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "fetch_base_image", {
        "id": _ID_BASE_IMAGE,
        "url": "https://fake-bucket.s3.us-east-2.amazonaws.com/base.png",
        "prompt": "p",
    })
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "image_editing", make_variations(indices))
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "prompt_analysis", _analyzed(indices))


def _resolution_ok(image_id: str, n: int = 1) -> dict[str, Any]:
    return {"id": image_id, "url": signed_url(f"library/{image_id}_ok.png", n), "prompt": ""}


def _resolution_failures(image_id: str) -> list[Any]:
    """4 rejected URL_Resolution outcomes: exception, foreign id, blank url, not a dict."""
    return [
        RuntimeError(f"sinergia 500 at {signed_url('library/err.png', 7)}"),
        {"id": "someone-else", "url": signed_url("library/other.png", 8), "prompt": ""},
        {"id": image_id, "url": "   ", "prompt": ""},
        ["not", "a", "dict"],
    ]


# ---------------------------------------------------------------------------
# 13.3 / 13.5 — happy paths and Edit_Instruction
# ---------------------------------------------------------------------------


def test_custom_prompt_only_three_variations_done():
    """13.3: Edit_Instruction == custom_prompt; DONE with 3 Registered_Variant whose
    ids come from upload_image_to_library and urls from each id's URL_Resolution."""
    with patched_pipeline() as h:
        result = _run(n_variations=3)

    assert h.edit.call_count == 1
    assert h.edit.calls[0]["edit_instruction"] == _CUSTOM_PROMPT
    assert result["status"] == "DONE"
    assert result["task_id"] == _TASK_ID
    assert result["variant_id"] == 5
    assert result["id_base_image"] == _ID_BASE_IMAGE
    assert len(result["variations"]) == 3
    ids = h.upload.uploaded_ids
    assert len(ids) == 3 and len(set(ids)) == 3
    assert [v["id"] for v in result["variations"]] == ids
    assert h.get_ad_variant_image.resolved_ids == ids
    assert [v["url"] for v in result["variations"]] == h.get_ad_variant_image.resolution_urls
    assert all(set(v) == {"id", "url", "prompt"} for v in result["variations"])


def test_expand_zoom_option_plus_custom_prompt_instruction():
    """13.5: translation + single space + custom_prompt."""
    with patched_pipeline() as h:
        result = _run(expand_zoom_option="ZOOM_1_5X", n_variations=1)

    expected = translate_expand_zoom_option("ZOOM_1_5X") + " " + _CUSTOM_PROMPT
    assert h.edit.calls[0]["edit_instruction"] == expected
    assert result["status"] == "DONE"
    assert len(result["variations"]) == 1


# ---------------------------------------------------------------------------
# 13.6 — download failures (network error, timeout, non-2xx)
# ---------------------------------------------------------------------------


def _real_download_with(handler):
    """Download outcome that runs the real helper over an httpx.MockTransport."""
    transport = httpx.MockTransport(handler)

    def _outcome(url: str, task_id: str, *args: Any, **kwargs: Any):
        return _REAL_DOWNLOAD(url, task_id, transport=transport)

    return _outcome


def _raise(exc: Exception):
    def _handler(request: httpx.Request) -> httpx.Response:
        raise exc
    return _handler


def test_download_failures_raise_download_error_without_editing_or_upload():
    """13.6: network error, timeout and non-2xx → FuryException of step `download`;
    0 calls to the editor, upload_image_to_library and Edit_Sleep."""
    cases = {
        "network": _raise(httpx.ConnectError("connection refused")),
        "timeout": _raise(httpx.ReadTimeout("read timed out")),
        "non_2xx": lambda request: httpx.Response(503, content=b"unavailable"),
    }
    for name, handler in cases.items():
        download = FakeDownloadBaseImage([_real_download_with(handler)])
        with patched_pipeline(download=download) as h:
            exc = _run_expect(BaseImageDownloadError)

        assert isinstance(exc, FuryException), name
        assert exc.details["step"] == "download", name
        assert exc.details["id_base_image"] == _ID_BASE_IMAGE, name
        assert exc.retryable is True, name
        assert h.download.call_count == 1, name
        assert h.edit.call_count == 0, name
        assert h.upload.call_count == 0, name
        assert h.sleep.call_count == 0, name


# ---------------------------------------------------------------------------
# 13.7 — Base_Image without url
# ---------------------------------------------------------------------------


def test_base_image_without_url_is_non_retryable():
    """13.7: missing / None / empty / blank url → non-retryable FuryException."""
    for base in (
        {"id": _ID_BASE_IMAGE, "prompt": "p"},
        {"id": _ID_BASE_IMAGE, "url": None, "prompt": "p"},
        {"id": _ID_BASE_IMAGE, "url": "", "prompt": "p"},
        {"id": _ID_BASE_IMAGE, "url": "   ", "prompt": "p"},
    ):
        with patched_pipeline(get_ad_variant_image=FakeGetAdVariantImage([base])) as h:
            exc = _run_expect(BaseImageUrlMissingError)

        assert isinstance(exc, FuryException)
        assert exc.retryable is False
        assert jrs._is_retryable_edit_error(exc) is False
        assert exc.details["id_base_image"] == _ID_BASE_IMAGE
        assert h.download.call_count == 0
        assert h.edit.call_count == 0
        assert h.upload.call_count == 0


# ---------------------------------------------------------------------------
# 13.8 / 13.9 — NanoBanana2 failures
# ---------------------------------------------------------------------------


def test_all_variations_fail_raises_image_editing_error():
    """13.8: 0 variations → step `image_editing`; no prompter, no upload, no checkpoint."""
    with patched_pipeline(edit=FakeEditImageVariations([[]])) as h:
        exc = _run_expect(ImageEditingFailedError)

    assert isinstance(exc, FuryException)
    assert exc.details["step"] == "image_editing"
    assert h.run_agent.call_count == 0
    assert h.upload.call_count == 0
    assert h.sleep.call_count == 0
    assert h.get_ad_variant_image.resolution_call_count == 0
    assert h.redis.checkpoint(_TASK_ID, _AD_ID, "image_editing") is None


def test_one_variation_fails_returns_two():
    """13.9: n=3 with 1 NanoBanana2 failure → DONE with 2 Registered_Variant."""
    edit = FakeEditImageVariations([FakeEditImageVariations.succeed_only([1, 3])])
    with patched_pipeline(edit=edit) as h:
        result = _run(n_variations=3)

    assert result["status"] == "DONE"
    assert len(result["variations"]) == 2
    assert h.upload.call_count == 2
    assert [p["image_name"] for p in h.upload.payloads] == ["banner_1", "banner_3"]


# ---------------------------------------------------------------------------
# 13.11 — Variant_Prompter fallback
# ---------------------------------------------------------------------------


def test_prompter_failure_falls_back_to_edit_instruction():
    """13.11: n=2, one prompter failure (exception / validator rejection)."""
    good = "A sunny beach behind the product"
    for failure in (RuntimeError("LLM down"), '{"image_prompt": ""}', "not json at all"):
        run_agent = FakeRunAgent([failure, {"image_prompt": good}])
        with patched_pipeline(run_agent=run_agent) as h:
            result = _run(n_variations=2)

        assert h.run_agent.call_count == 2
        prompts = [v["prompt"] for v in result["variations"]]
        assert prompts == [_CUSTOM_PROMPT, good], (failure, prompts)


# ---------------------------------------------------------------------------
# 13.12 / 13.13 — upload failures
# ---------------------------------------------------------------------------


def test_partial_upload_failures_keep_successful_one():
    """13.12: n=3; 1 upload raises, 1 returns "" → 1 Registered_Variant."""
    upload = FakeUploadImageToLibrary([RuntimeError("sinergia 500"), DEFAULT, ""])
    with patched_pipeline(upload=upload) as h:
        result = _run(n_variations=3)

    assert h.upload.call_count == 3
    assert result["status"] == "DONE"
    assert len(result["variations"]) == 1
    ok_ids = h.upload.uploaded_ids
    assert len(ok_ids) == 1
    assert result["variations"][0]["id"] == ok_ids[0]
    # Only the uploaded image is resolved, and its URL_Resolution url is returned.
    assert h.get_ad_variant_image.resolved_ids == ok_ids
    assert result["variations"][0]["url"] == h.get_ad_variant_image.resolution_urls[0]
    # The surviving variation is the 2nd one (index-suffixed name).
    assert h.upload.payloads[1]["image_name"] == "banner_2"


def test_variation_name_has_no_double_extension():
    """13.32: `image_name` with extension (`banner.png` / `banner.jpg`) and `image/png`
    variations → `image_name` sent without extension, so Sinergia's filename
    (`image_name` + guess_extension(mime_type)) is `banner_1.png`, not `banner_1.png.png`."""
    for image_name in ("banner.png", "banner.jpg"):
        edit = FakeEditImageVariations(mime_type="image/png")
        with patched_pipeline(edit=edit) as h:
            result = _run(image_name=image_name, n_variations=1)

        assert result["status"] == "DONE", image_name
        payload = h.upload.payloads[0]
        assert payload["mime_type"] == "image/png", image_name
        assert payload["image_name"] == "banner_1", image_name
        filename = payload["image_name"] + mimetypes.guess_extension(payload["mime_type"])
        assert filename == "banner_1.png", image_name


def test_all_uploads_fail_then_retry_reuses_prompt_analysis():
    """13.13: total upload failure → step `upload`, no upload checkpoint; the retry
    reuses `prompt_analysis` (no prompter / editor / fetch / download again).
    Neither Edit_Sleep nor URL_Resolution run when no upload succeeds."""
    redis = FakeRedis()
    upload = FakeUploadImageToLibrary([RuntimeError("boom"), "", RuntimeError("boom")])
    with patched_pipeline(redis=redis, upload=upload) as h:
        exc = _run_expect(VariationUploadFailedError, task=FakeTask(_TASK_ID), n_variations=3)

        assert isinstance(exc, FuryException)
        assert exc.details["step"] == "upload"
        assert exc.retryable is True
        assert redis.checkpoint(_TASK_ID, _AD_ID, "upload") is None
        assert h.sleep.call_count == 0
        assert h.get_ad_variant_image.resolution_call_count == 0
        analysis = redis.checkpoint(_TASK_ID, _AD_ID, "prompt_analysis")
        assert analysis is not None and len(analysis) == 3
        calls_before = (
            h.get_ad_variant_image.base_call_count, h.download.call_count,
            h.edit.call_count, h.run_agent.call_count,
        )
        assert calls_before == (1, 1, 1, 3)

        # Retry (same task_id, same Redis): uploads now succeed.
        result = _run(task=FakeTask(_TASK_ID, retries=1), n_variations=3)

        assert (
            h.get_ad_variant_image.base_call_count, h.download.call_count,
            h.edit.call_count, h.run_agent.call_count,
        ) == calls_before
        assert h.upload.call_count == 6
        assert result["status"] == "DONE"
        assert [v["prompt"] for v in result["variations"]] == [a["prompt"] for a in analysis]
        assert redis.checkpoint(_TASK_ID, _AD_ID, "upload") is not None
        assert h.sleep.calls == [_LIBRARY_INDEX_DELAY_S]
        assert h.get_ad_variant_image.resolution_call_count == 3


# ---------------------------------------------------------------------------
# 13.16 / 13.23 — checkpoints on retry
# ---------------------------------------------------------------------------


def test_preloaded_checkpoints_skip_to_upload():
    """13.16: fetch/editing/analysis checkpoints → only upload (once per variation)
    and URL_Resolution (once per Uploaded_Image) run; no Base_Image call."""
    redis = FakeRedis()
    _seed_until_analysis(redis, [1, 2])
    task = FakeTask(_TASK_ID, retries=1)
    with patched_pipeline(redis=redis, id_base_image=_ID_BASE_IMAGE) as h:
        result = _run(task=task, n_variations=2)

    assert h.get_ad_variant_image.base_call_count == 0
    assert h.download.call_count == 0
    assert h.edit.call_count == 0
    assert h.run_agent.call_count == 0
    assert h.upload.call_count == 2
    assert h.get_ad_variant_image.resolved_ids == h.upload.uploaded_ids
    assert [v["prompt"] for v in result["variations"]] == [
        "checkpoint prompt 1", "checkpoint prompt 2",
    ]
    # Progress is emitted for every step, in order, even when skipped (Req 11.11).
    assert task.steps == _PROGRESS_ORDER


def test_retry_with_fetch_checkpoint_refreshes_url():
    """13.23: fetch checkpoint without image_editing → get_ad_variant_image once and
    the download uses the fresh URL, not the (stripped) checkpoint URL."""
    stale_url = "https://fake-bucket.s3.us-east-2.amazonaws.com/stale_base.png"
    redis = FakeRedis()
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "fetch_base_image", {
        "id": _ID_BASE_IMAGE, "url": stale_url, "prompt": "old prompt",
    })
    fresh = {"id": _ID_BASE_IMAGE, "url": signed_url("fresh_base.png", 99), "prompt": "p"}
    get_image = FakeGetAdVariantImage([fresh])
    with patched_pipeline(redis=redis, get_ad_variant_image=get_image) as h:
        result = _run(task=FakeTask(_TASK_ID, retries=1), n_variations=2)

    assert h.get_ad_variant_image.base_call_count == 1
    assert h.get_ad_variant_image.returned_urls == [fresh["url"]]
    assert h.download.urls == [fresh["url"]]
    assert stale_url not in h.download.urls
    assert h.edit.call_count == 1
    assert result["status"] == "DONE"
    # The fetch checkpoint does not need rewriting.
    assert redis.writes_for(cp_key(_TASK_ID, _AD_ID, "fetch_base_image")) == []


def test_progress_sequence_in_order():
    """Req 11.11: the 7 PROGRESS steps (incl. `resolve_urls`) on a full first run."""
    task = FakeTask(_TASK_ID)
    with patched_pipeline():
        _run(task=task, n_variations=1)

    assert task.steps == _PROGRESS_ORDER
    assert len(task.steps) == 7
    assert all(u["state"] == "PROGRESS" for u in task.updates)
    assert all(set(u["meta"]) == {"step", "detail"} for u in task.updates)


# ---------------------------------------------------------------------------
# 13.24 – 13.28 / 13.30 — resolve_urls (Edit_Sleep + URL_Resolution)
# ---------------------------------------------------------------------------


class _EventLog:
    """Shared, ordered log of upload / sleep / URL_Resolution calls."""

    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []


class _LoggedUpload(FakeUploadImageToLibrary):
    def __init__(self, log: _EventLog, script: Any = None) -> None:
        super().__init__(script)
        self._log = log

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._log.events.append(("upload", None))
        return await super().__call__(*args, **kwargs)


class _LoggedSleep(FakeSleep):
    def __init__(self, log: _EventLog) -> None:
        super().__init__()
        self._log = log

    async def __call__(self, seconds: float, *args: Any, **kwargs: Any) -> None:
        self._log.events.append(("sleep", seconds))
        await super().__call__(seconds, *args, **kwargs)


class _LoggedGet(FakeGetAdVariantImage):
    def __init__(self, log: _EventLog, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._log = log

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        before = self.resolution_call_count
        result = await super().__call__(*args, **kwargs)
        kind = "resolve" if self.resolution_call_count > before else "base"
        self._log.events.append((kind, None))
        return result


def test_library_index_delay_called_once_with_15s():
    """13.24: Edit_Sleep(15) exactly once, after the last upload and before the
    first URL_Resolution; nothing waits in real time."""
    log = _EventLog()
    with patched_pipeline(
        upload=_LoggedUpload(log), sleep=_LoggedSleep(log), get_ad_variant_image=_LoggedGet(log),
    ) as h:
        result = _run(n_variations=3)

    assert result["status"] == "DONE"
    assert h.sleep.calls == [_LIBRARY_INDEX_DELAY_S]
    kinds = [k for k, _ in log.events]
    sleep_at = kinds.index("sleep")
    last_upload = max(i for i, k in enumerate(kinds) if k == "upload")
    first_resolve = kinds.index("resolve")
    assert last_upload < sleep_at < first_resolve
    assert kinds.count("upload") == 3 and kinds.count("resolve") == 3


def test_url_resolution_retries_then_succeeds():
    """13.25: exception, foreign id, blank url, then valid → 4 URL_Resolution,
    waits [15, 5, 5, 5] and the variation keeps the valid url."""
    image_id = "lib-1"
    valid = _resolution_ok(image_id, 42)
    get_image = FakeGetAdVariantImage(resolutions={image_id: [
        RuntimeError("sinergia 500"),
        {"id": "someone-else", "url": signed_url("library/other.png", 8), "prompt": ""},
        {"id": image_id, "url": "  ", "prompt": ""},
        valid,
    ]})
    upload = FakeUploadImageToLibrary([image_id])
    with patched_pipeline(get_ad_variant_image=get_image, upload=upload) as h:
        result = _run(n_variations=1)

    assert len(h.get_ad_variant_image.resolution_calls_for(image_id)) == 4
    assert h.sleep.calls == [
        _LIBRARY_INDEX_DELAY_S, _RESOLVE_URL_RETRY_DELAY_S,
        _RESOLVE_URL_RETRY_DELAY_S, _RESOLVE_URL_RETRY_DELAY_S,
    ]
    assert result["status"] == "DONE"
    assert result["variations"] == [
        {"id": image_id, "url": valid["url"], "prompt": result["variations"][0]["prompt"]},
    ]


def test_url_resolution_exhausted_omits_variation():
    """13.25: 4 rejected URL_Resolution → variation omitted, sanitized log, no 5th query."""
    bad, good = "lib-1", "lib-2"
    get_image = FakeGetAdVariantImage(resolutions={
        # A 5th (valid) outcome would be consumed only by a forbidden 5th query.
        bad: _resolution_failures(bad) + [_resolution_ok(bad, 99)],
    })
    upload = FakeUploadImageToLibrary([bad, good])
    with patched_pipeline(get_ad_variant_image=get_image, upload=upload) as h:
        result = _run(n_variations=2)

    assert len(h.get_ad_variant_image.resolution_calls_for(bad)) == 4
    assert len(h.get_ad_variant_image.resolution_calls_for(good)) == 1
    assert result["status"] == "DONE"
    assert [v["id"] for v in result["variations"]] == [good]
    skipped = [line for line in h.logs.lines if "skipped" in line and bad in line]
    assert skipped, h.logs.text
    assert all(f"[{_TASK_ID}]" in line and "4" in line for line in skipped)
    assert "X-Amz-Signature" not in h.logs.text
    assert "X-Amz-Credential" not in h.logs.text


def test_resume_from_upload_checkpoint_does_not_reupload():
    """13.26: `upload` checkpoint without `resolve_urls` → 0 uploads / editor /
    prompter / download; Edit_Sleep(15) once; 1 URL_Resolution per image."""
    redis = FakeRedis()
    _seed_until_analysis(redis, [1, 2])
    uploaded = [{"id": "lib-1", "prompt": "p1"}, {"id": "lib-2", "prompt": "p2"}]
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "upload", uploaded)
    with patched_pipeline(redis=redis, id_base_image=_ID_BASE_IMAGE) as h:
        result = _run(task=FakeTask(_TASK_ID, retries=1), n_variations=2)

    assert h.upload.call_count == 0
    assert h.edit.call_count == 0
    assert h.run_agent.call_count == 0
    assert h.download.call_count == 0
    assert h.get_ad_variant_image.base_call_count == 0
    assert h.sleep.calls == [_LIBRARY_INDEX_DELAY_S]
    assert h.get_ad_variant_image.resolved_ids == ["lib-1", "lib-2"]
    assert [v["id"] for v in result["variations"]] == ["lib-1", "lib-2"]
    assert [v["prompt"] for v in result["variations"]] == ["p1", "p2"]
    assert redis.checkpoint(_TASK_ID, _AD_ID, "resolve_urls") is not None


def test_resume_from_resolve_urls_checkpoint():
    """13.27: `resolve_urls` checkpoint → 0 uploads, 0 Edit_Sleep, 0 URL_Resolution;
    result built from the checkpoint's Registered_Variants."""
    redis = FakeRedis()
    _seed_until_analysis(redis, [1, 2])
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "upload", [
        {"id": "lib-1", "prompt": "p1"}, {"id": "lib-2", "prompt": "p2"},
    ])
    registered = [
        {"id": "lib-1", "url": "https://fake-bucket.s3.us-east-2.amazonaws.com/l1.png", "prompt": "p1"},
        {"id": "lib-2", "url": "https://fake-bucket.s3.us-east-2.amazonaws.com/l2.png", "prompt": "p2"},
    ]
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "resolve_urls", registered)
    task = FakeTask(_TASK_ID, retries=1)
    with patched_pipeline(redis=redis, id_base_image=_ID_BASE_IMAGE) as h:
        result = _run(task=task, n_variations=2)

    assert h.upload.call_count == 0
    assert h.sleep.call_count == 0
    assert h.get_ad_variant_image.call_count == 0
    assert result["status"] == "DONE"
    assert result["variations"] == registered
    assert task.steps == _PROGRESS_ORDER


def test_all_url_resolutions_fail_raises_and_retry_does_not_reupload():
    """13.28: every URL_Resolution fails → retryable VariationUrlResolutionError of
    step `resolve_urls`; `upload` checkpoint kept, no `resolve_urls` checkpoint;
    the retry calls upload_image_to_library 0 times."""
    ids = ["lib-1", "lib-2"]
    redis = FakeRedis()
    get_image = FakeGetAdVariantImage(resolutions={i: _resolution_failures(i) for i in ids})
    upload = FakeUploadImageToLibrary(list(ids))
    with patched_pipeline(redis=redis, get_ad_variant_image=get_image, upload=upload) as h:
        exc = _run_expect(VariationUrlResolutionError, task=FakeTask(_TASK_ID), n_variations=2)

        assert isinstance(exc, VariationUploadFailedError)
        assert isinstance(exc, FuryException)
        assert exc.retryable is True
        assert jrs._is_retryable_edit_error(exc) is True
        assert exc.details["step"] == "resolve_urls"
        assert [u["id"] for u in redis.checkpoint(_TASK_ID, _AD_ID, "upload")] == ids
        assert redis.checkpoint(_TASK_ID, _AD_ID, "resolve_urls") is None
        assert h.get_ad_variant_image.resolution_call_count == 8
        assert h.upload.call_count == 2

        # Retry (same Redis): resolutions now succeed, nothing is re-uploaded.
        result = _run(task=FakeTask(_TASK_ID, retries=1), n_variations=2)

        assert h.upload.call_count == 2
        assert result["status"] == "DONE"
        assert [v["id"] for v in result["variations"]] == ids
        assert h.get_ad_variant_image.resolution_call_count == 10
        assert redis.checkpoint(_TASK_ID, _AD_ID, "resolve_urls") is not None


def test_upload_checkpoint_has_only_id_and_prompt():
    """13.30: the `upload` checkpoint is a list of `{id, prompt}` items only."""
    with patched_pipeline() as h:
        _run(n_variations=2)

    cp = h.redis.checkpoint(_TASK_ID, _AD_ID, "upload")
    assert isinstance(cp, list) and len(cp) == 2
    assert all(set(item) == {"id", "prompt"} for item in cp)
    assert [item["id"] for item in cp] == h.upload.uploaded_ids


# ---------------------------------------------------------------------------
# __main__ runner (PYTHONPATH=. python -m tests.test_ad_variant_image_edit_pipeline)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import sys
    import traceback

    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
