"""Property-based tests for the ad-variant image-edit pipeline.

Run:  PYTHONPATH=. env/bin/python -m pytest tests/test_ad_variant_image_edit_pipeline_properties.py
  or: PYTHONPATH=. env/bin/python -m tests.test_ad_variant_image_edit_pipeline_properties

Everything runs in memory: downloads go through `httpx.MockTransport`, the rest
of the pipeline uses the fakes of `tests/_edit_pipeline_fakes.py`, and
`network_guard()` turns any real outbound call into a failure (Req 13.1, 13.2).
"""
from __future__ import annotations

import asyncio
import base64
import copy
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
from hypothesis import assume, given, settings, strategies as st

from core.exceptions import (
    BaseImageDownloadError,
    BaseImageMismatchError,
    BaseImageUrlMissingError,
    ImageEditingFailedError,
    VariationUploadFailedError,
    VariationUrlResolutionError,
)
from schemas.pipeline_schemas import ExpandZoomOption
from services import job_runner_service as jrs
from services.edit_instruction import build_edit_instruction
from tests._edit_pipeline_fakes import (
    CHECKPOINT_TTL,
    DEFAULT_BASE_PROMPT,
    DEFAULT_IMAGE_BYTES,
    FakeDownloadBaseImage,
    FakeEditImageVariations,
    FakeGetAdVariantImage,
    FakeRedis,
    FakeRunAgent,
    FakeSleep,
    FakeTask,
    FakeUploadImageToLibrary,
    cp_key,
    network_guard,
    patched_pipeline,
    signed_url,
)

# Real function, captured before any patching (patched_pipeline replaces the
# module attribute with a fake for the duration of the context).
_REAL_DOWNLOAD = jrs._download_base_image

_TASK_ID = "prop-task-id"
_ID_BASE_IMAGE = "base-img-123"
_URL = (
    "https://fake-bucket.s3.us-east-2.amazonaws.com/base.png"
    "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=fakesig"
)

_PIPELINE_KWARGS: dict[str, Any] = dict(
    brand_id=1,
    campaign_id=2,
    ad_id=3,
    channel_id=4,
    variant_id=5,
    image_name="banner.png",
    id_base_image=_ID_BASE_IMAGE,
    n_variations=2,
    custom_prompt=None,
    expand_zoom_option="ZOOM_2X",
)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

_token = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-.",
    min_size=1,
    max_size=12,
)
_media_type = st.one_of(
    st.sampled_from([
        "image/png", "image/jpeg", "image/webp", "image/gif", "IMAGE/PNG", "Image/Jpeg",
        "text/html", "application/json", "application/octet-stream", "text/plain",
        "imagex/png", "image", "image/",
    ]),
    st.tuples(st.sampled_from(["image", "text", "application", "video"]), _token).map("/".join),
    _token,
)
_params = st.one_of(
    st.just(""),
    st.sampled_from(["; charset=utf-8", ";charset=binary", "; charset=ISO-8859-1"]),
    _token.map(lambda t: f"; charset={t}"),
    st.tuples(_token, _token).map(lambda t: f"; {t[0]}={t[1]}"),
)
_content_type = st.one_of(
    st.none(),
    st.tuples(st.sampled_from(["", " "]), _media_type, _params).map(lambda t: "".join(t)),
)
_status = st.one_of(
    st.integers(min_value=200, max_value=299),
    st.integers(min_value=100, max_value=599),
    st.sampled_from([100, 101, 199, 200, 204, 299, 300, 302, 304, 400, 404, 500, 503, 599]),
)
_body = st.one_of(st.just(b""), st.binary(min_size=1, max_size=256), st.binary(max_size=8))

_TRANSPORT_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.ReadError,
    httpx.WriteError,
    httpx.RemoteProtocolError,
    httpx.NetworkError,
)


@dataclass(frozen=True)
class _Reply:
    status: int
    body: bytes
    content_type: str | None


@dataclass(frozen=True)
class _Failure:
    exc_type: type[httpx.TransportError]
    message: str


_scenario = st.one_of(
    st.builds(_Reply, status=_status, body=_body, content_type=_content_type),
    st.builds(
        _Failure,
        exc_type=st.sampled_from(_TRANSPORT_ERRORS),
        message=st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=20),
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _expected(scenario: _Reply | _Failure) -> tuple[bytes, str] | None:
    """Oracle: `(body, mime)` iff 2xx ∧ body ≥ 1 byte ∧ (no CT ∨ CT is image/*)."""
    if isinstance(scenario, _Failure):
        return None
    if not 200 <= scenario.status < 300 or len(scenario.body) < 1:
        return None
    if scenario.content_type is None:
        return scenario.body, "image/png"
    mime = scenario.content_type.split(";", 1)[0].strip().lower()
    if not mime.startswith("image/"):
        return None
    return scenario.body, mime


def _transport(scenario: _Reply | _Failure, seen: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if isinstance(scenario, _Failure):
            raise scenario.exc_type(scenario.message, request=request)
        headers = {} if scenario.content_type is None else {"Content-Type": scenario.content_type}
        # 1xx/3xx are returned as final responses: MockTransport has no interim
        # responses and, without a Location header, httpx never follows a 3xx.
        return httpx.Response(scenario.status, headers=headers, content=scenario.body)

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Property 9
# ---------------------------------------------------------------------------


# Feature: ad-variant-image-edit-pipeline, Property 9: Clasificación de la descarga
@settings(max_examples=100, deadline=None)
@given(scenario=_scenario)
def test_property_9_download_classification(scenario: _Reply | _Failure) -> None:
    """**Validates: Requirements 5.2, 5.4, 5.5, 13.6**"""
    expected = _expected(scenario)

    # ── _download_base_image in isolation ───────────────────────────────────
    seen: list[httpx.Request] = []
    with network_guard():
        try:
            result = asyncio.run(
                _REAL_DOWNLOAD(_URL, _TASK_ID, transport=_transport(scenario, seen))
            )
            outcome: Any = result
        except jrs._DownloadRejected as exc:
            outcome = exc
        except httpx.HTTPError as exc:
            outcome = exc

    assert len(seen) == 1 and str(seen[0].url) == _URL  # exactly one attempt per call
    if expected is not None:
        body, mime = outcome
        assert body == expected[0]  # byte-identical
        assert mime == expected[1]
    elif isinstance(scenario, _Failure):
        assert type(outcome) is scenario.exc_type  # transport errors propagate as-is
    else:
        assert isinstance(outcome, jrs._DownloadRejected)
        assert isinstance(outcome.cause, str) and outcome.cause.strip()

    # ── pipeline-level mapping ─────────────────────────────────────────────
    pipeline_seen: list[httpx.Request] = []

    async def real_download(url: str, task_id: str) -> tuple[bytes, str]:
        return await _REAL_DOWNLOAD(url, task_id, transport=_transport(scenario, pipeline_seen))

    with patched_pipeline(download=FakeDownloadBaseImage([real_download])) as h:
        try:
            pipeline_result = asyncio.run(
                jrs._run_edit_ad_variant_image_pipeline(
                    FakeTask(task_id=_TASK_ID), _TASK_ID, **_PIPELINE_KWARGS
                )
            )
            error: BaseException | None = None
        except Exception as exc:  # noqa: BLE001 - classified below
            error = exc
            pipeline_result = None

    assert h.download.call_count == 1 and len(pipeline_seen) == 1
    if expected is not None:
        assert error is None, f"unexpected {type(error).__name__}: {error}"
        assert pipeline_result is not None and pipeline_result["status"] == "DONE"
        assert h.edit.call_count == 1
        assert h.edit.calls[0]["base_image_bytes"] == expected[0]
        assert h.edit.calls[0]["base_mime_type"] == expected[1]
    else:
        assert isinstance(error, BaseImageDownloadError), repr(error)
        assert error.retryable is True
        assert error.code == BaseImageDownloadError.code
        assert error.details["step"] == "download"
        assert error.details["id_base_image"] == _ID_BASE_IMAGE
        cause = error.details.get("cause")
        assert isinstance(cause, str) and cause.strip()
        assert h.edit.call_count == 0  # Image_Editor never invoked
        assert h.upload.call_count == 0


# ---------------------------------------------------------------------------
# Property 8
# ---------------------------------------------------------------------------

# Plain ids: _redact_text leaves them untouched, so details can be compared verbatim.
_plain_id = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
    min_size=1,
    max_size=24,
)
_MISSING_KEY = object()  # sentinel: "url" key absent from the Base_Image
_blank_url = st.one_of(
    st.just(_MISSING_KEY),
    st.none(),
    st.text(alphabet=" \t\n\r\f\v", max_size=8),  # "" or whitespace only
)


@st.composite
def _guard_scenario(draw: st.DrawFn) -> tuple[str, str, dict[str, Any]]:
    """(kind, id_base_image, base) where base triggers exactly one guard."""
    id_base_image = draw(_plain_id)
    if draw(st.booleans()):
        received = draw(_plain_id.filter(lambda v: v != id_base_image))
        url = draw(st.one_of(st.just(_URL), _blank_url))  # id check comes first
        base: dict[str, Any] = {"id": received, "prompt": DEFAULT_BASE_PROMPT}
        if url is not _MISSING_KEY:
            base["url"] = url
        return "mismatch", id_base_image, base
    url = draw(_blank_url)
    base = {"id": id_base_image, "prompt": DEFAULT_BASE_PROMPT}
    if url is not _MISSING_KEY:
        base["url"] = url
    return "url_missing", id_base_image, base


# Feature: ad-variant-image-edit-pipeline, Property 8: Guardas no reintentables de la Base_Image
@settings(max_examples=100, deadline=None)
@given(scenario=_guard_scenario())
def test_property_8_base_image_non_retryable_guards(
    scenario: tuple[str, str, dict[str, Any]],
) -> None:
    """**Validates: Requirements 4.9, 5.3, 11.5, 13.7**"""
    kind, id_base_image, base = scenario
    kwargs = {**_PIPELINE_KWARGS, "id_base_image": id_base_image}

    get = FakeGetAdVariantImage([base], base_image_id=id_base_image)
    with patched_pipeline(get_ad_variant_image=get, id_base_image=id_base_image) as h:
        try:
            asyncio.run(
                jrs._run_edit_ad_variant_image_pipeline(
                    FakeTask(task_id=_TASK_ID), _TASK_ID, **kwargs
                )
            )
            error: BaseException | None = None
        except Exception as exc:  # noqa: BLE001 - classified below
            error = exc

    # Only the Base_Image call (request's id_base_image); no URL_Resolution happens.
    assert h.get_ad_variant_image.base_call_count == 1
    assert h.get_ad_variant_image.resolution_calls == []
    if kind == "mismatch":
        assert isinstance(error, BaseImageMismatchError), repr(error)
        assert error.details["expected_id"] == id_base_image
        assert error.details["received_id"] == base["id"]
    else:
        assert isinstance(error, BaseImageUrlMissingError), repr(error)
        assert error.details["step"] == "download"
    assert error.retryable is False
    assert type(error).retryable is False
    assert error.details["id_base_image"] == id_base_image

    # No fetch_base_image checkpoint and no downstream work.
    fetch_key = cp_key(_TASK_ID, kwargs["ad_id"], "fetch_base_image")
    assert h.redis.writes_for(fetch_key) == []
    assert fetch_key not in h.redis.data
    assert h.download.call_count == 0
    assert h.edit.call_count == 0
    assert h.run_agent.call_count == 0
    assert h.prompter_factory.call_count == 0
    assert h.upload.call_count == 0


# ---------------------------------------------------------------------------
# Property 11
# ---------------------------------------------------------------------------

_WORDS = st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ", min_size=1, max_size=60)
_PAD = st.text(alphabet=" \t\n", max_size=3)
# Agent prompt: non-blank text with optional surrounding whitespace (expected = strip).
_agent_prompt = st.tuples(_PAD, _WORDS.filter(lambda s: s.strip()), _PAD).map("".join)
_custom_prompt = st.one_of(st.none(), _WORDS.map(str.strip).filter(bool))
_option = st.one_of(st.none(), st.sampled_from([o.value for o in ExpandZoomOption]))

# Prompter outcomes that must fall back to the Edit_Instruction (F_pr).
_prompter_failure = st.one_of(
    st.sampled_from([
        RuntimeError("prompter boom"),
        TimeoutError("prompter timeout"),
        "",
        "   ",
        "not json at all",
        "[]",
        '"just a string"',
        "{}",
        '{"image_prompt": "   "}',
        '{"image_prompt": 5}',
        '{"image_prompt": null}',
        '{"other": "x"}',
        '{"image_prompt": "' + "x" * 2001 + '"}',
        {"image_prompt": "  "},
        {"image_prompt": 7},
    ]),
)

# Upload outcomes that make a variation omitted (F_up): upload_image_to_library
# returns the library id as `str`; an exception, `""`/blank or any non-`str`
# value is an omitted variation (Req 9.7).
_upload_failure = st.sampled_from([
    RuntimeError("sinergia 500"),
    ConnectionError("sinergia down"),
    "",
    "   ",
    None,
    5,
    {},
    {"image_id": "img-x"},
    ["img-x"],
])

# Permanent URL_Resolution failure kinds (F_res): every one of the 4 queries fails.
_RES_FAILURE_KINDS = ("raise", "not_dict", "none", "id_mismatch", "url_missing", "url_blank", "url_none")


def _resolution_failure(kind: str, image_id: str) -> Any:
    if kind == "raise":
        return RuntimeError("sinergia GET 404")
    if kind == "not_dict":
        return "not a dict"
    if kind == "none":
        return None
    if kind == "id_mismatch":
        return {"id": f"{image_id}-other", "url": signed_url(f"library/{image_id}.png", 9)}
    if kind == "url_missing":
        return {"id": image_id, "prompt": ""}
    if kind == "url_blank":
        return {"id": image_id, "url": "  ", "prompt": ""}
    return {"id": image_id, "url": None, "prompt": ""}


def _resolved_url(i: int) -> str:
    """URL returned by the URL_Resolution of variation i (presigned on purpose:
    the result must carry it unmodified, Req 10.3)."""
    return signed_url(f"library/img-{i}.png", i)


@dataclass(frozen=True)
class _E2EScenario:
    n: int
    ok_gen: tuple[int, ...]  # editor successes (1-based, ascending)
    mime: str
    option: str | None
    custom_prompt: str | None
    agent: tuple[tuple[bool, Any], ...]  # per ok_gen: (fails?, outcome)
    upload: tuple[tuple[bool, Any], ...]  # per ok_gen: (fails?, outcome)
    res_fail: tuple[tuple[int, tuple[str, ...]], ...]  # F_res: (index, 4 failure kinds)


@st.composite
def _e2e_scenario(draw: st.DrawFn) -> _E2EScenario:
    n = draw(st.integers(min_value=1, max_value=10))
    f_gen = draw(st.sets(st.integers(1, n), max_size=n - 1))  # proper subset
    ok_gen = tuple(i for i in range(1, n + 1) if i not in f_gen)
    f_pr = draw(st.sets(st.sampled_from(ok_gen)))
    f_up = draw(st.sets(st.sampled_from(ok_gen), max_size=len(ok_gen) - 1))  # ≥ 1 upload OK
    ok_up = [i for i in ok_gen if i not in f_up]
    f_res = draw(st.sets(st.sampled_from(ok_up), max_size=len(ok_up) - 1))  # ≥ 1 resolved
    option = draw(_option)
    custom_prompt = draw(_custom_prompt)
    assume(option is not None or custom_prompt is not None)
    agent = []
    upload = []
    for i in ok_gen:
        if i in f_pr:
            agent.append((True, draw(_prompter_failure)))
        else:
            text = draw(_agent_prompt)
            as_json = draw(st.booleans())
            agent.append((False, json.dumps({"image_prompt": text}) if as_json else {"image_prompt": text}))
        upload.append((True, draw(_upload_failure)) if i in f_up else (False, None))
    res_fail = tuple(
        (i, tuple(draw(st.lists(st.sampled_from(_RES_FAILURE_KINDS), min_size=4, max_size=4))))
        for i in sorted(f_res)
    )
    return _E2EScenario(
        n=n,
        ok_gen=ok_gen,
        mime=draw(st.sampled_from(["image/png", "image/jpeg", "image/webp"])),
        option=option,
        custom_prompt=custom_prompt,
        agent=tuple(agent),
        upload=tuple(upload),
        res_fail=res_fail,
    )


# Feature: ad-variant-image-edit-pipeline, Property 11: Invariante end-to-end del resultado
@settings(max_examples=100, deadline=None)
@given(sc=_e2e_scenario())
def test_property_11_end_to_end_result_invariant(sc: _E2EScenario) -> None:
    """**Validates: Requirements 4.11, 6.10, 6.11, 7.8, 8.7, 8.8, 8.9, 8.10, 8.12, 9.4,
    9.5, 9.7, 9.9, 9.12, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.8, 14.3, 14.4, 14.6,
    14.11, 13.3, 13.9, 13.11, 13.12, 13.19**"""
    kwargs = {
        **_PIPELINE_KWARGS,
        "n_variations": sc.n,
        "expand_zoom_option": sc.option,
        "custom_prompt": sc.custom_prompt,
    }
    instruction = build_edit_instruction(sc.option, sc.custom_prompt)
    variations = FakeEditImageVariations.succeed_only(sc.ok_gen, sc.mime)
    b64_by_index = {v["index"]: v["image_b64"] for v in variations}

    # Expected prompt per editor success.
    expected_prompt: dict[int, str] = {}
    for i, (fails, outcome) in zip(sc.ok_gen, sc.agent):
        expected_prompt[i] = instruction if fails else (
            json.loads(outcome)["image_prompt"] if isinstance(outcome, str) else outcome["image_prompt"]
        ).strip()

    # Shared event log to check ordering across fakes (upload → resolutions).
    events: list[tuple[str, str]] = []

    # Upload outcomes as async callables that detect concurrent invocation.
    in_flight = {"now": 0, "max": 0}

    def _uploader(i: int, fails: bool, outcome: Any):
        async def _call(*_a: Any, **_k: Any) -> Any:
            in_flight["now"] += 1
            in_flight["max"] = max(in_flight["max"], in_flight["now"])
            events.append(("upload", str(i)))
            try:
                await asyncio.sleep(0)  # yield: a concurrent caller would overlap here
                if not fails:
                    return f"img-{i}"
                if isinstance(outcome, BaseException):
                    raise outcome
                return copy.deepcopy(outcome)
            finally:
                in_flight["now"] -= 1
        return _call

    def _resolver(image_id: str, outcome: Any):
        def _call(*_a: Any, **_k: Any) -> Any:
            events.append(("resolve", image_id))
            if isinstance(outcome, BaseException):
                raise outcome
            return copy.deepcopy(outcome)
        return _call

    res_fail = dict(sc.res_fail)
    upload_script = []
    resolutions: dict[str, list[Any]] = {}
    uploaded: list[int] = []  # editor indices uploaded OK, in order
    for i, (fails, outcome) in zip(sc.ok_gen, sc.upload):
        upload_script.append(_uploader(i, fails, outcome))
        if fails:
            continue
        uploaded.append(i)
        image_id = f"img-{i}"
        if i in res_fail:
            resolutions[image_id] = [
                _resolver(image_id, _resolution_failure(kind, image_id)) for kind in res_fail[i]
            ]
        else:
            resolutions[image_id] = [
                _resolver(image_id, {"id": image_id, "url": _resolved_url(i), "prompt": ""})
            ]
    expected_ok = [i for i in uploaded if i not in res_fail]  # registered, editor order

    edit = FakeEditImageVariations([variations], mime_type=sc.mime)
    run_agent = FakeRunAgent([outcome for _, outcome in sc.agent])
    upload = FakeUploadImageToLibrary(upload_script)
    get = FakeGetAdVariantImage(resolutions=resolutions, base_image_id=_ID_BASE_IMAGE)
    sleep = FakeSleep()

    with patched_pipeline(
        edit=edit, run_agent=run_agent, upload=upload, get_ad_variant_image=get,
        sleep=sleep, id_base_image=_ID_BASE_IMAGE,
    ) as h:
        result = asyncio.run(
            jrs._run_edit_ad_variant_image_pipeline(FakeTask(task_id=_TASK_ID), _TASK_ID, **kwargs)
        )

    # ── editor: exact bytes and Edit_Instruction ────────────────────────────
    assert h.get_ad_variant_image.base_call_count == 1
    assert h.edit.call_count == 1
    call = h.edit.calls[0]
    assert call["base_image_bytes"] == DEFAULT_IMAGE_BYTES
    assert call["edit_instruction"] == instruction
    assert call["n_variations"] == sc.n

    # ── prompter: once per Edited_Variation ────────────────────────────────
    assert h.run_agent.call_count == len(sc.ok_gen)
    for i, c in zip(sc.ok_gen, h.run_agent.calls):
        assert c["image_data"] == f"data:{sc.mime};base64,{b64_by_index[i]}"

    # ── upload: once per analyzed variation, sequential, exact payload ─────
    assert h.upload.call_count == len(sc.ok_gen)
    assert in_flight["max"] == 1
    names = []
    for i, c in zip(sc.ok_gen, h.upload.calls):
        assert c["ad_id"] == kwargs["ad_id"]
        payload = c["image_data"]
        assert set(payload) == {"image_data", "image_name", "mime_type", "image_prompt"}
        assert payload["image_data"] == f"data:{sc.mime};base64,{b64_by_index[i]}"
        assert payload["mime_type"] == sc.mime
        assert payload["image_prompt"] == expected_prompt[i]
        name = payload["image_name"]
        assert name == jrs._variation_image_name(kwargs["image_name"], i)
        assert name.endswith(f"_{i}")
        assert name == f"banner_{i}"  # fixture "banner.png": extension dropped
        names.append(name)
    assert len(set(names)) == len(names)

    # ── URL_Resolution: only uploaded ids, after the last upload, bounded ──
    uploaded_ids = [f"img-{i}" for i in uploaded]
    failed_up_ids = {f"img-{i}" for i, (fails, _) in zip(sc.ok_gen, sc.upload) if fails}
    expected_resolved_ids = [
        f"img-{i}" for i in uploaded for _ in range(4 if i in res_fail else 1)
    ]
    assert h.get_ad_variant_image.resolved_ids == expected_resolved_ids
    assert not failed_up_ids & set(h.get_ad_variant_image.resolved_ids)
    for c in h.get_ad_variant_image.resolution_calls:
        for key in ("brand_id", "campaign_id", "ad_id", "channel_id", "variant_id", "image_name"):
            assert c[key] == kwargs[key]
    last_upload = max(k for k, (kind, _) in enumerate(events) if kind == "upload")
    first_resolve = min(k for k, (kind, _) in enumerate(events) if kind == "resolve")
    assert first_resolve > last_upload
    # Edit_Sleep: 15 s once, then 5 s between the 4 queries of each F_res id.
    assert h.sleep.calls == [15] + [5] * (3 * len(res_fail))

    # ── result shape ───────────────────────────────────────────────────────
    assert set(result) == {"task_id", "variant_id", "id_base_image", "status", "variations"}
    assert result["status"] == "DONE"
    assert result["task_id"] == _TASK_ID
    assert result["variant_id"] == kwargs["variant_id"]
    assert result["id_base_image"] == kwargs["id_base_image"]
    out = result["variations"]
    n_up_failed = len(failed_up_ids)
    assert len(out) == sc.n - (sc.n - len(sc.ok_gen)) - n_up_failed - len(res_fail)
    assert len(uploaded_ids) + n_up_failed == len(sc.ok_gen)  # uploaded + omitted == analyzed
    assert len(out) + len(res_fail) == len(uploaded_ids)  # registered + omitted == uploaded
    assert [(v["id"], v["url"]) for v in out] == [(f"img-{i}", _resolved_url(i)) for i in expected_ok]
    assert len({v["id"] for v in out}) == len(out)
    for v, i in zip(out, expected_ok):
        assert set(v) == {"id", "url", "prompt"}
        assert all(isinstance(v[k], str) and v[k] for k in ("id", "url", "prompt"))
        assert v["prompt"] == expected_prompt[i]

    # ── no image data in the serialized result ─────────────────────────────
    blob = json.dumps(result)
    assert "data:" not in blob
    assert base64.b64encode(DEFAULT_IMAGE_BYTES).decode() not in blob
    for b64 in b64_by_index.values():
        assert b64 not in blob


# ---------------------------------------------------------------------------
# Property 12
# ---------------------------------------------------------------------------


@st.composite
def _total_failure_scenario(draw: st.DrawFn) -> tuple[str, int, tuple[int, ...], tuple[Any, ...]]:
    """(kind, n, ok_gen, failures).
    kind == "editing": the editor returns no variation (failures == ());
    kind == "upload": n' >= 1 variations, every upload fails (one F_up outcome each);
    kind == "resolve": every upload succeeds and every URL_Resolution fails
    (4 F_res kinds per uploaded id, one per bounded query)."""
    kind = draw(st.sampled_from(["editing", "upload", "resolve"]))
    n = draw(st.integers(min_value=1, max_value=10))
    if kind == "editing":
        return kind, n, (), ()
    ok_gen = tuple(sorted(draw(st.sets(st.integers(1, n), min_size=1))))
    if kind == "upload":
        failures = tuple(draw(_upload_failure) for _ in ok_gen)
    else:
        failures = tuple(
            tuple(draw(st.lists(st.sampled_from(_RES_FAILURE_KINDS), min_size=4, max_size=4)))
            for _ in ok_gen
        )
    return kind, n, ok_gen, failures


# Feature: ad-variant-image-edit-pipeline, Property 12: Fallos totales por paso
@settings(max_examples=100, deadline=None)
@given(sc=_total_failure_scenario())
def test_property_12_total_failures_per_step(
    sc: tuple[str, int, tuple[int, ...], tuple[Any, ...]],
) -> None:
    """**Validates: Requirements 7.9, 7.10, 9.8, 14.7, 13.8, 13.13, 13.28**"""
    kind, n, ok_gen, failures = sc
    kwargs = {**_PIPELINE_KWARGS, "n_variations": n}
    edit = FakeEditImageVariations([FakeEditImageVariations.succeed_only(ok_gen)])
    resolutions: dict[str, list[Any]] = {}
    if kind == "resolve":
        uploaded_ids = [f"img-{i}" for i in ok_gen]
        upload = FakeUploadImageToLibrary(uploaded_ids)
        for image_id, kinds in zip(uploaded_ids, failures):
            resolutions[image_id] = [_resolution_failure(k, image_id) for k in kinds]
    else:
        uploaded_ids = []
        upload = FakeUploadImageToLibrary(list(failures))
    get = FakeGetAdVariantImage(resolutions=resolutions, base_image_id=_ID_BASE_IMAGE)
    sleep = FakeSleep()

    with patched_pipeline(
        edit=edit, upload=upload, get_ad_variant_image=get,
        sleep=sleep, id_base_image=_ID_BASE_IMAGE,
    ) as h:
        try:
            asyncio.run(
                jrs._run_edit_ad_variant_image_pipeline(
                    FakeTask(task_id=_TASK_ID), _TASK_ID, **kwargs
                )
            )
            error: BaseException | None = None
        except Exception as exc:  # noqa: BLE001 - classified below
            error = exc

    ad_id = kwargs["ad_id"]
    editing_key = cp_key(_TASK_ID, ad_id, "image_editing")
    analysis_key = cp_key(_TASK_ID, ad_id, "prompt_analysis")
    upload_key = cp_key(_TASK_ID, ad_id, "upload")
    resolve_key = cp_key(_TASK_ID, ad_id, "resolve_urls")
    assert h.edit.call_count == 1
    assert h.edit.calls[0]["n_variations"] == n
    # resolve_urls never checkpoints on a total failure.
    assert h.redis.writes_for(resolve_key) == []
    assert resolve_key not in h.redis.data

    if kind == "editing":
        assert isinstance(error, ImageEditingFailedError), repr(error)
        assert error.details["step"] == "image_editing"
        # No image_editing checkpoint (nor later ones) and no downstream work.
        for key in (editing_key, analysis_key, upload_key):
            assert h.redis.writes_for(key) == []
            assert key not in h.redis.data
        assert h.prompter_factory.call_count == 0
        assert h.run_agent.call_count == 0
        assert h.upload.call_count == 0
        assert h.sleep.calls == []
        assert h.get_ad_variant_image.resolution_calls == []
    else:
        # prompt_analysis checkpoint present with n' entries, in editor order.
        analysis = h.redis.load(analysis_key)
        assert isinstance(analysis, list)
        assert len(analysis) == len(ok_gen)
        assert [v["index"] for v in analysis] == list(ok_gen)
        assert h.run_agent.call_count == len(ok_gen)
        assert h.upload.call_count == len(ok_gen)

    if kind == "upload":
        assert type(error) is VariationUploadFailedError, repr(error)
        assert error.details["step"] == "upload"
        # Upload checkpoint absent; 0 Edit_Sleep and 0 URL_Resolution.
        assert h.redis.writes_for(upload_key) == []
        assert upload_key not in h.redis.data
        assert h.sleep.calls == []
        assert h.get_ad_variant_image.resolution_calls == []
    elif kind == "resolve":
        assert type(error) is VariationUrlResolutionError, repr(error)
        assert isinstance(error, VariationUploadFailedError)
        assert error.details["step"] == "resolve_urls"
        # Upload checkpoint kept: one {"id", "prompt"} entry per successful upload.
        cp_upload = h.redis.load(upload_key)
        assert isinstance(cp_upload, list)
        assert [item["id"] for item in cp_upload] == uploaded_ids
        assert all(set(item) == {"id", "prompt"} for item in cp_upload)
        # Each id queried 4 times (bounded), sequentially and in upload order.
        assert h.get_ad_variant_image.resolved_ids == [i for i in uploaded_ids for _ in range(4)]
        assert h.sleep.calls == [15] + [5] * (3 * len(uploaded_ids))

    assert error.retryable is True
    assert type(error).retryable is True
    assert error.details["id_base_image"] == kwargs["id_base_image"]


# ---------------------------------------------------------------------------
# Property 13
# ---------------------------------------------------------------------------

_CP_STEPS = ("fetch_base_image", "image_editing", "prompt_analysis", "upload", "resolve_urls")
_PROGRESS_STEPS = [
    "fetch_base_image", "download", "image_editing", "prompt_analysis", "upload",
    "resolve_urls", "done",
]


@dataclass(frozen=True)
class _ResumeScenario:
    n: int
    ok_gen: tuple[int, ...]
    agent: tuple[Any, ...]  # prompter outcome per editor success
    signed_url: tuple[bool, ...]  # per editor success: URL_Resolution returns a presigned url
    prefix_len: int  # |S|, S = _CP_STEPS[:prefix_len]


@st.composite
def _resume_scenario(draw: st.DrawFn) -> _ResumeScenario:
    n = draw(st.integers(min_value=1, max_value=6))
    ok_gen = tuple(sorted(draw(st.sets(st.integers(1, n), min_size=1))))
    agent = tuple(
        draw(st.one_of(
            _agent_prompt.map(lambda t: {"image_prompt": t}),
            _agent_prompt.map(lambda t: json.dumps({"image_prompt": t})),
            _prompter_failure,
        ))
        for _ in ok_gen
    )
    signed = tuple(draw(st.booleans()) for _ in ok_gen)
    return _ResumeScenario(
        n=n, ok_gen=ok_gen, agent=agent, signed_url=signed,
        prefix_len=draw(st.integers(min_value=0, max_value=len(_CP_STEPS))),
    )


def _resume_url(i: int, signed: bool) -> str:
    return _resolved_url(i) if signed else f"https://fake-sinergia.local/library/img-{i}.png"


def _resume_fakes(sc: _ResumeScenario) -> dict[str, Any]:
    """Fresh, identically scripted fakes: deterministic library ids (`img-{i}`)
    and URL_Resolution accepted on the first query with a fixed url per id."""
    resolutions = {
        f"img-{i}": [{"id": f"img-{i}", "url": _resume_url(i, s), "prompt": ""}]
        for i, s in zip(sc.ok_gen, sc.signed_url)
    }
    return dict(
        get_ad_variant_image=FakeGetAdVariantImage(
            resolutions=resolutions, base_image_id=_ID_BASE_IMAGE
        ),
        download=FakeDownloadBaseImage(),
        edit=FakeEditImageVariations([FakeEditImageVariations.succeed_only(sc.ok_gen)]),
        run_agent=FakeRunAgent(list(sc.agent)),
        upload=FakeUploadImageToLibrary([f"img-{i}" for i in sc.ok_gen]),
        sleep=FakeSleep(),
        id_base_image=_ID_BASE_IMAGE,
    )


# Feature: ad-variant-image-edit-pipeline, Property 13: Reanudación por checkpoints equivalente
@settings(max_examples=100, deadline=None)
@given(sc=_resume_scenario())
def test_property_13_checkpoint_resume_equivalent(sc: _ResumeScenario) -> None:
    """**Validates: Requirements 4.7, 4.8, 7.11, 7.12, 8.11, 9.10, 9.11, 11.7, 11.8, 11.9,
    11.10, 11.11, 14.1, 14.8, 14.9, 14.10, 13.16, 13.26, 13.27, 13.30**"""
    kwargs = {**_PIPELINE_KWARGS, "n_variations": sc.n}
    ad_id = kwargs["ad_id"]
    keys = {step: cp_key(_TASK_ID, ad_id, step) for step in _CP_STEPS}
    uploaded_ids = [f"img-{i}" for i in sc.ok_gen]

    # ── reference run (no checkpoints) ─────────────────────────────────────
    ref_task = FakeTask(task_id=_TASK_ID)
    with patched_pipeline(**_resume_fakes(sc)) as ref:
        ref_result = asyncio.run(
            jrs._run_edit_ad_variant_image_pipeline(ref_task, _TASK_ID, **kwargs)
        )
    ref_cps = {step: ref.redis.checkpoint(_TASK_ID, ad_id, step) for step in _CP_STEPS}
    assert all(v is not None for v in ref_cps.values())
    assert ref_task.steps == _PROGRESS_STEPS
    assert ref.sleep.calls == [15]
    assert ref.get_ad_variant_image.resolved_ids == uploaded_ids
    # upload checkpoint: exactly {id, prompt} per Uploaded_Image, editor order.
    assert [item["id"] for item in ref_cps["upload"]] == uploaded_ids
    assert all(set(item) == {"id", "prompt"} for item in ref_cps["upload"])
    ref_payloads = ref.upload.payloads

    # ── resumed run with prefix S preloaded ────────────────────────────────
    prefix = set(_CP_STEPS[: sc.prefix_len])
    redis = FakeRedis()
    for step in prefix:
        redis.seed_checkpoint(_TASK_ID, ad_id, step, ref_cps[step])
    task = FakeTask(task_id=_TASK_ID)
    with patched_pipeline(redis=redis, **_resume_fakes(sc)) as h:
        result = asyncio.run(jrs._run_edit_ad_variant_image_pipeline(task, _TASK_ID, **kwargs))

    # ── collaborator invocations ───────────────────────────────────────────
    expected_fetch = 0 if "image_editing" in prefix else 1
    assert h.get_ad_variant_image.base_call_count == expected_fetch
    assert h.download.call_count == expected_fetch
    assert h.edit.call_count == (0 if "image_editing" in prefix else 1)
    assert h.run_agent.call_count == (0 if "prompt_analysis" in prefix else len(sc.ok_gen))
    assert h.upload.call_count == (0 if "upload" in prefix else len(sc.ok_gen))
    if "upload" not in prefix:
        assert h.upload.payloads == ref_payloads  # same work as the reference
    if "resolve_urls" in prefix:
        assert h.sleep.calls == []
        assert h.get_ad_variant_image.resolution_calls == []
    else:
        assert h.sleep.calls == [15]  # also when resuming from the upload checkpoint
        assert h.get_ad_variant_image.resolved_ids == uploaded_ids

    # ── checkpoint writes: steps in S untouched, steps outside S stored once ─
    for step in _CP_STEPS:
        writes = h.redis.writes_for(keys[step])
        if step in prefix:
            assert writes == []
        else:
            assert len(writes) == 1
            assert writes[0].decoded == ref_cps[step]
    for s in h.redis.sets:
        assert s.key in keys.values()
        assert s.ex == CHECKPOINT_TTL == 7200
        if s.key == keys["upload"]:
            assert all(set(item) == {"id", "prompt"} for item in s.decoded)

    # ── equivalent result (url sanitized when resumed from resolve_urls) ───
    expected = jrs._strip_signed_urls(ref_result) if "resolve_urls" in prefix else ref_result
    assert result == expected

    # ── PROGRESS steps always in the same order ────────────────────────────
    assert task.steps == _PROGRESS_STEPS


# ---------------------------------------------------------------------------
# Property 18
# ---------------------------------------------------------------------------

_ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_hex = st.text(alphabet="0123456789abcdef", min_size=16, max_size=24)
# Realistic API keys (no '*', which would interact with the "***" mask).
_api_key = st.text(alphabet=_ALNUM + "_", min_size=16, max_size=40)
_task_id = st.uuids().map(str)
# Log lines emitted by the edit pipeline code paths (coroutine, _progress,
# _download_base_image, checkpoint helpers) are bound with this logger name via
# core.logging.get_logger(__name__). Other modules / libraries may log too, so
# the `[{task_id}]` prefix check is scoped to these lines; the "nothing
# sensitive" check applies to every captured line regardless of origin.
_PIPELINE_LOGGER = "services.job_runner_service"
_SIGNING_MARKER_RE = re.compile(r"(?i:x-amz-)|Signature=|GoogleAccessId=|Key-Pair-Id=")
_B64_DATA_RE = re.compile(r";base64,[A-Za-z0-9+/=_-]")


@dataclass(frozen=True)
class _Signing:
    credential: str
    token: str
    signature: str

    def url(self, path: str) -> str:
        """Realistic SigV4 presigned S3 URL."""
        return (
            f"https://fake-bucket.s3.us-east-2.amazonaws.com/{path}"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256"
            f"&X-Amz-Credential={self.credential}%2F20250101%2Fus-east-2%2Fs3%2Faws4_request"
            "&X-Amz-Date=20250101T000000Z&X-Amz-Expires=3600"
            f"&X-Amz-Security-Token={self.token}"
            f"&X-Amz-SignedHeaders=host&X-Amz-Signature={self.signature}"
        )

    @property
    def values(self) -> tuple[str, ...]:
        return (self.credential, self.token, self.signature)


_signing = st.builds(
    _Signing,
    credential=_hex.map(lambda h: "AKIA" + h.upper()),
    token=_hex.map(lambda h: "FwoGZXIvYXdzE" + h),
    signature=_hex.map(lambda h: "SigVal" + h * 2),
)

_FAIL_STEPS = (
    "none",
    "fetch_raise",         # get_ad_variant_image raises
    "fetch_mismatch",      # returned id (with signed URL + key) != id_base_image
    "download_transport",  # real _download_base_image, transport error embeds the URL
    "download_rejected",   # real _download_base_image, leaky non-image Content-Type
    "download_raise",      # download raises a generic exception
    "edit_raise",          # Image_Editor raises
    "edit_empty",          # Image_Editor returns []
    "prompter_raise",      # every run_agent call raises
    "upload_raise_some",   # first upload raises, the rest succeed
    "upload_raise_all",    # every upload raises
    "resolve_flaky",       # each id: first URL_Resolution query fails (leaky), then resolves
    "resolve_fail_some",   # first id: all 4 queries fail (leaky), the rest resolve
    "resolve_fail_all",    # every id: all 4 queries fail → VariationUrlResolutionError
)

# Leaky URL_Resolution failures: an exception whose message carries the signed
# URL / data-URI / keys, or a response whose (mismatched) id embeds them.
_RES_LEAK_KINDS = ("raise", "mismatch")


@dataclass(frozen=True)
class _LeakScenario:
    task_id: str
    use_task: bool
    sinergia_key: str
    internal_key: str
    signing: _Signing
    leak_b64: str  # data-URI payload embedded in failure messages
    image_bytes: bytes
    variation_bytes: tuple[bytes, ...]  # one per variation (n = len)
    signed_resolution: bool  # URL_Resolution returns presigned URLs
    res_kinds: tuple[str, ...]  # 4 leaky failure kinds, one per bounded query
    fail: str


# Distinctive prefixes so a secret can never coincide with legitimate data
# (raw variation base64 in checkpoints, task ids, plain URLs) while shrinking.
_leak_scenario = st.builds(
    _LeakScenario,
    task_id=_task_id,
    use_task=st.booleans(),
    sinergia_key=_api_key.map(lambda k: "sk-sinergia-" + k),
    internal_key=_api_key.map(lambda k: "sk-internal-" + k),
    signing=_signing,
    leak_b64=st.binary(min_size=12, max_size=48).map(
        lambda b: "LeakB64" + base64.b64encode(b).decode()
    ),
    image_bytes=st.binary(min_size=1, max_size=64),
    variation_bytes=st.lists(st.binary(min_size=1, max_size=48), min_size=1, max_size=3).map(tuple),
    signed_resolution=st.booleans(),
    res_kinds=st.lists(st.sampled_from(_RES_LEAK_KINDS), min_size=4, max_size=4).map(tuple),
    fail=st.sampled_from(_FAIL_STEPS),
)


def _res_leak(sc: _LeakScenario, kind: str, image_id: str) -> Any:
    """One rejected URL_Resolution query whose content carries every secret."""
    url = sc.signing.url(f"library/{image_id}.png")
    if kind == "raise":
        return RuntimeError(_leak_message(sc, url, "sinergia GET resolution"))
    return {"id": f"{image_id}-other {_leak_message(sc, url, 'mismatch')}", "url": url, "prompt": ""}


def _leak_message(sc: _LeakScenario, url: str, label: str) -> str:
    """Failure message carrying every kind of secret (signed URL, data-URI, keys)."""
    return (
        f"{label} failed for {url} payload=data:image/png;base64,{sc.leak_b64} "
        f"key={sc.sinergia_key} internal={sc.internal_key}"
    )


def _assert_no_secrets(text: str, sc: _LeakScenario, where: str) -> None:
    for value in (*sc.signing.values, sc.sinergia_key, sc.internal_key, sc.leak_b64):
        assert value not in text, f"secret {value!r} leaked in {where}: {text!r}"
    assert not _SIGNING_MARKER_RE.search(text), f"signing param in {where}: {text!r}"
    assert not _B64_DATA_RE.search(text), f"data-URI payload in {where}: {text!r}"


# Feature: ad-variant-image-edit-pipeline, Property 18: Nada sensible en logs, checkpoints ni details
@settings(max_examples=100, deadline=None)
@given(sc=_leak_scenario)
def test_property_18_nothing_sensitive_in_logs_checkpoints_details(sc: _LeakScenario) -> None:
    """**Validates: Requirements 4.7, 5.6, 7.7, 9.7, 12.4, 12.5, 12.6, 12.10, 14.6, 13.22**"""
    from core.exceptions import FuryException

    n = len(sc.variation_bytes)
    kwargs = {**_PIPELINE_KWARGS, "n_variations": n}
    base_url = sc.signing.url(f"base_{kwargs['variant_id']}.png")

    # ── get_ad_variant_image ───────────────────────────────────────────────
    base = {"id": _ID_BASE_IMAGE, "url": base_url, "prompt": DEFAULT_BASE_PROMPT}
    if sc.fail == "fetch_raise":
        get_script: list[Any] = [RuntimeError(_leak_message(sc, base_url, "sinergia GET"))]
    elif sc.fail == "fetch_mismatch":
        get_script = [{**base, "id": f"other {base_url} {sc.sinergia_key}"}]
    else:
        get_script = [base]

    # ── download: real _download_base_image over MockTransport ─────────────
    def handler(request: httpx.Request) -> httpx.Response:
        if sc.fail == "download_transport":
            raise httpx.ConnectError(
                _leak_message(sc, str(request.url), "connect"), request=request
            )
        if sc.fail == "download_rejected":
            ct = f"text/html; note={_leak_message(sc, str(request.url), 'ct')}"
            return httpx.Response(200, headers={"Content-Type": ct}, content=b"<html/>")
        return httpx.Response(200, headers={"Content-Type": "image/png"}, content=sc.image_bytes)

    async def download(url: str, task_id: str) -> tuple[bytes, str]:
        if sc.fail == "download_raise":
            raise RuntimeError(_leak_message(sc, url, "download"))
        return await _REAL_DOWNLOAD(url, task_id, transport=httpx.MockTransport(handler))

    # ── editor / prompter / upload ─────────────────────────────────────────
    variations = [
        {"index": i, "image_b64": base64.b64encode(b).decode(), "mime_type": "image/png"}
        for i, b in enumerate(sc.variation_bytes, start=1)
    ]
    if sc.fail == "edit_raise":
        edit_script: list[Any] = [RuntimeError(_leak_message(sc, base_url, "nanobanana"))]
    elif sc.fail == "edit_empty":
        edit_script = [[]]
    else:
        edit_script = [variations]
    agent_script: list[Any] = (
        [RuntimeError(_leak_message(sc, base_url, "prompter")) for _ in range(n)]
        if sc.fail == "prompter_raise" else []
    )

    # Upload returns the library id as `str`; failures raise with leaky messages.
    upload_script: list[Any] = []
    uploaded_ids: list[str] = []
    for i in range(1, n + 1):
        raises = sc.fail == "upload_raise_all" or (sc.fail == "upload_raise_some" and i == 1)
        if raises:
            upload_script.append(
                RuntimeError(_leak_message(sc, sc.signing.url(f"edited_{i}.png"), "sinergia POST"))
            )
        else:
            upload_script.append(f"img-{i}")
            uploaded_ids.append(f"img-{i}")

    # ── URL_Resolution: signed (or plain) URLs, leaky rejected queries ─────
    def _resolved(image_id: str) -> dict[str, str]:
        url = (
            sc.signing.url(f"library/{image_id}.png") if sc.signed_resolution
            else f"https://fake-sinergia.local/library/{image_id}.png"
        )
        return {"id": image_id, "url": url, "prompt": ""}

    resolutions: dict[str, list[Any]] = {}
    for k, image_id in enumerate(uploaded_ids):
        if sc.fail == "resolve_fail_all" or (sc.fail == "resolve_fail_some" and k == 0):
            resolutions[image_id] = [_res_leak(sc, kind, image_id) for kind in sc.res_kinds]
        elif sc.fail == "resolve_flaky":
            resolutions[image_id] = [_res_leak(sc, sc.res_kinds[0], image_id), _resolved(image_id)]
        else:
            resolutions[image_id] = [_resolved(image_id)]

    task = FakeTask(task_id=sc.task_id) if sc.use_task else None
    with patched_pipeline(
        get_ad_variant_image=FakeGetAdVariantImage(
            get_script, resolutions=resolutions, base_image_id=_ID_BASE_IMAGE
        ),
        download=FakeDownloadBaseImage([download]),
        edit=FakeEditImageVariations(edit_script),
        run_agent=FakeRunAgent(agent_script),
        upload=FakeUploadImageToLibrary(upload_script),
        sleep=FakeSleep(),
        id_base_image=_ID_BASE_IMAGE,
        sinergia_api_key=sc.sinergia_key,
        internal_api_key=sc.internal_key,
    ) as h:
        try:
            asyncio.run(jrs._run_edit_ad_variant_image_pipeline(task, sc.task_id, **kwargs))
            error: BaseException | None = None
        except Exception as exc:  # noqa: BLE001 - inspected below
            error = exc

    # With n == 1, "*_some" makes every upload / URL_Resolution fail.
    succeeded = sc.fail in ("none", "prompter_raise", "resolve_flaky") or (
        sc.fail in ("upload_raise_some", "resolve_fail_some") and n > 1
    )
    reached_resolve = succeeded or sc.fail in ("resolve_fail_some", "resolve_fail_all")
    if succeeded:
        assert error is None, repr(error)
    else:
        assert error is not None
    if reached_resolve and not succeeded:
        assert type(error) is VariationUrlResolutionError, repr(error)
        assert error.details["step"] == "resolve_urls"

    # ── logs: nothing sensitive (any origin), `[{task_id}]` on pipeline lines ─
    assert h.logs is not None
    for record in h.logs.records:
        _assert_no_secrets(record.message, sc, f"log ({record.logger_name})")
    pipeline_lines = [r.message for r in h.logs.records if r.logger_name == _PIPELINE_LOGGER]
    assert pipeline_lines, "the pipeline emitted no log line"
    for line in pipeline_lines:
        assert line.startswith(f"[{sc.task_id}]"), f"log line without prefix: {line!r}"

    # ── checkpoints (every _store) and PROGRESS meta ───────────────────────
    for s in h.redis.sets:
        _assert_no_secrets(s.value, sc, f"checkpoint {s.key}")
    # `upload` / `resolve_urls` checkpoints are actually written (so the scan
    # above covers them) whenever the run reaches / completes resolve_urls.
    ad_id = kwargs["ad_id"]
    upload_writes = h.redis.writes_for(cp_key(sc.task_id, ad_id, "upload"))
    resolve_writes = h.redis.writes_for(cp_key(sc.task_id, ad_id, "resolve_urls"))
    if reached_resolve:
        assert len(upload_writes) == 1
        assert [item["id"] for item in upload_writes[0].decoded] == uploaded_ids
        assert all(set(item) == {"id", "prompt"} for item in upload_writes[0].decoded)
        assert h.get_ad_variant_image.resolution_calls, "no URL_Resolution happened"
    if succeeded:
        assert len(resolve_writes) == 1
        assert resolve_writes[0].decoded, "empty resolve_urls checkpoint"
    else:
        assert resolve_writes == []
    for w in (*upload_writes, *resolve_writes):
        _assert_no_secrets(w.value, sc, f"checkpoint {w.key}")
    if task is not None:
        _assert_no_secrets(json.dumps(task.updates), sc, "PROGRESS meta")

    # ── details (and message) of the pipeline's FuryException ─────────────
    if isinstance(error, FuryException):
        _assert_no_secrets(json.dumps(error.details, default=str), sc, "details")
        _assert_no_secrets(error.message, sc, "exception message")


# ── _redact_text over arbitrary text ───────────────────────────────────────

_signed_fragment = st.builds(
    lambda host, name, value, marker: f"https://{host}.example.com/a.png?{marker}{name}={value}",
    host=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
    name=st.sampled_from(["Credential", "Security-Token", "Signature", "Date", "Expires"]),
    value=_hex.map(lambda h: "SigVal" + h),
    marker=st.sampled_from(["X-Amz-", "x-amz-", "X-AMZ-", "foo=1&X-Amz-"]),
)
_other_signed_fragment = st.builds(
    lambda param, value, as_url: (
        f"https://cdn.example.com/x.png?{param}={value}" if as_url else f"{param}={value}"
    ),
    param=st.sampled_from(["Signature", "GoogleAccessId", "Key-Pair-Id", "X-Amz-Signature"]),
    value=_hex.map(lambda h: "SigVal" + h),
    as_url=st.booleans(),
)
_data_uri_fragment = st.builds(
    lambda mime, payload: f"data:{mime};base64,{payload}",
    mime=st.sampled_from(["image/png", "image/jpeg", "application/octet-stream", "text/plain"]),
    payload=st.binary(min_size=9, max_size=64).map(
        lambda b: "LeakB64" + base64.b64encode(b).decode()
    ),
)


@st.composite
def _redact_input(draw: st.DrawFn) -> tuple[str, str, str]:
    sinergia_key = draw(_api_key)
    internal_key = draw(_api_key)
    fragments = draw(st.lists(
        st.one_of(
            st.text(max_size=20),
            _signed_fragment,
            _other_signed_fragment,
            _data_uri_fragment,
            st.just(sinergia_key),
            st.just(internal_key),
        ),
        max_size=8,
    ))
    seps = draw(st.lists(st.sampled_from(["", " ", "\n", "'", '"', "&", "<", ": "]),
                         min_size=len(fragments), max_size=len(fragments)))
    text = "".join(f + s for f, s in zip(fragments, seps))
    return text, sinergia_key, internal_key


# Feature: ad-variant-image-edit-pipeline, Property 18: Nada sensible en logs, checkpoints ni details
@settings(max_examples=100, deadline=None)
@given(data=_redact_input())
def test_property_18_redact_text_arbitrary_text(data: tuple[str, str, str]) -> None:
    """**Validates: Requirements 4.7, 5.6, 7.7, 9.7, 12.4, 12.5, 12.6, 13.22**"""
    text, sinergia_key, internal_key = data
    with patched_pipeline(
        sinergia_api_key=sinergia_key, internal_api_key=internal_key, capture_logs=False,
    ):
        out = jrs._redact_text(text)

    assert isinstance(out, str) and len(out) <= 300
    assert not _SIGNING_MARKER_RE.search(out), f"signing marker survived: {out!r}"
    assert not _B64_DATA_RE.search(out), f"data-URI payload survived: {out!r}"
    assert sinergia_key not in out and internal_key not in out
    # Payload / signature values that were in the input are gone (generated
    # with distinctive prefixes so they cannot coincide with free text).
    for m in re.finditer(r"(LeakB64[A-Za-z0-9+/=]+|SigVal[0-9a-f]+)", text):
        assert m.group(1) not in out, f"{m.group(1)!r} survived: {out!r}"


def test_redact_text_adjacent_data_uris_both_redacted() -> None:
    """Regression: a data-URI must not swallow the ``data`` of the next one,
    leaving the second payload unredacted.

    **Validates: Requirements 12.4, 12.5**
    """
    text = "data:image/png;base64,AAAAdata:image/png;base64,SECRETPAYLOAD"
    with patched_pipeline(capture_logs=False):
        out = jrs._redact_text(text)

    assert "AAAA" not in out, out
    assert "SECRETPAYLOAD" not in out, out
    assert not _B64_DATA_RE.search(out), out


# ---------------------------------------------------------------------------
# Property 19
# ---------------------------------------------------------------------------

_path_seg = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=12)
# Sanitized checkpoint URL: arbitrary host/path, never any signing parameter.
_sanitized_url = st.one_of(
    st.tuples(_path_seg, _path_seg).map(lambda t: f"https://{t[0]}.example.com/{t[1]}.png"),
    st.tuples(_path_seg, _path_seg, _path_seg).map(
        lambda t: f"https://{t[0]}.s3.amazonaws.com/{t[1]}/{t[2]}.jpg?v=1"
    ),
    st.just(""),
)
# Distinctive prefixes so the fresh prompt can never be confused with the checkpoint one.
_fresh_prompt = _WORDS.map(lambda w: "FRESHPROMPT " + w.strip())
_ckpt_prompt = _WORDS.map(lambda w: "CKPTPROMPT " + w.strip())


@dataclass(frozen=True)
class _FreshUrlScenario:
    cp_url: str
    cp_prompt: str
    fresh_url: str
    fresh_prompt: str
    received_id: str  # == _ID_BASE_IMAGE when matching


@st.composite
def _fresh_url_scenario(draw: st.DrawFn) -> _FreshUrlScenario:
    fresh_url = signed_url(f"fresh_{draw(_path_seg)}.png", draw(_hex))
    matching = draw(st.booleans())
    received = _ID_BASE_IMAGE if matching else draw(_plain_id.filter(lambda v: v != _ID_BASE_IMAGE))
    sc = _FreshUrlScenario(
        cp_url=draw(_sanitized_url),
        cp_prompt=draw(_ckpt_prompt),
        fresh_url=fresh_url,
        fresh_prompt=draw(_fresh_prompt),
        received_id=received,
    )
    assert sc.fresh_url != sc.cp_url
    return sc


# Feature: ad-variant-image-edit-pipeline, Property 19: El reintento descarga siempre desde una URL fresca
@settings(max_examples=100, deadline=None)
@given(sc=_fresh_url_scenario())
def test_property_19_retry_downloads_from_fresh_url(sc: _FreshUrlScenario) -> None:
    """**Validates: Requirements 4.8, 4.9, 5.1, 5.4, 11.8, 13.23**"""
    ad_id = _PIPELINE_KWARGS["ad_id"]
    fetch_key = cp_key(_TASK_ID, ad_id, "fetch_base_image")
    preloaded = {"id": _ID_BASE_IMAGE, "url": sc.cp_url, "prompt": sc.cp_prompt}
    redis = FakeRedis()
    redis.seed_checkpoint(_TASK_ID, ad_id, "fetch_base_image", preloaded)
    raw_before = redis.data[fetch_key]
    fresh = {"id": sc.received_id, "url": sc.fresh_url, "prompt": sc.fresh_prompt}

    get = FakeGetAdVariantImage([fresh], base_image_id=_ID_BASE_IMAGE)
    with patched_pipeline(
        redis=redis, get_ad_variant_image=get, id_base_image=_ID_BASE_IMAGE
    ) as h:
        try:
            result = asyncio.run(
                jrs._run_edit_ad_variant_image_pipeline(
                    FakeTask(task_id=_TASK_ID, retries=1), _TASK_ID, **_PIPELINE_KWARGS
                )
            )
            error: BaseException | None = None
        except Exception as exc:  # noqa: BLE001 - classified below
            error, result = exc, None

    # Count only Base_Image calls (request's id_base_image); URL_Resolution excluded.
    assert h.get_ad_variant_image.base_call_count == 1
    assert all(
        str(c.arguments["id_base_image"]) == _ID_BASE_IMAGE
        for c in h.get_ad_variant_image.base_calls
    )
    assert h.get_ad_variant_image.returned_urls == [sc.fresh_url]
    if sc.received_id == _ID_BASE_IMAGE:
        assert error is None, repr(error)
        assert result is not None and result["status"] == "DONE"
        assert h.download.call_count == 1
        assert h.download.urls == [sc.fresh_url]
        assert sc.cp_url not in h.download.urls
        # The prompter receives the fresh Base_Image prompt, not the checkpoint one.
        assert h.run_agent.call_count >= 1
        for message in h.run_agent.messages:
            assert f"Base image prompt: {sc.fresh_prompt}" in message
            assert sc.cp_prompt not in message
    else:
        assert isinstance(error, BaseImageMismatchError), repr(error)
        assert error.retryable is False
        assert h.download.call_count == 0
        assert h.edit.call_count == 0

    # Checkpoint fetch_base_image untouched in both cases.
    assert h.redis.writes_for(fetch_key) == []
    assert h.redis.data[fetch_key] == raw_before
    assert h.redis.load(fetch_key) == preloaded


# Feature: ad-variant-image-edit-pipeline, Property 19: El reintento descarga siempre desde una URL fresca
@settings(max_examples=100, deadline=None)
@given(
    k=st.integers(min_value=1, max_value=3),
    failures=st.lists(
        st.sampled_from([
            httpx.ConnectError("connect refused"),
            httpx.ReadTimeout("read timeout"),
            jrs._DownloadRejected("status 503"),
            jrs._DownloadRejected("empty body"),
        ]),
        min_size=3,
        max_size=3,
    ),
)
def test_property_19_each_attempt_downloads_from_its_own_fresh_url(
    k: int, failures: list[BaseException]
) -> None:
    """**Validates: Requirements 4.8, 4.9, 5.1, 5.4, 11.8, 13.23**"""
    ad_id = _PIPELINE_KWARGS["ad_id"]
    fetch_key = cp_key(_TASK_ID, ad_id, "fetch_base_image")
    # default: new signed URL on every Base_Image call
    get_fake = FakeGetAdVariantImage(base_image_id=_ID_BASE_IMAGE)
    download = FakeDownloadBaseImage(failures[:k])  # k failures, then success
    redis = FakeRedis()

    outcomes: list[BaseException | None] = []
    with patched_pipeline(
        redis=redis, get_ad_variant_image=get_fake, download=download,
        id_base_image=_ID_BASE_IMAGE,
    ) as h:
        for attempt in range(k + 1):
            # Count only Base_Image calls (request's id_base_image); URL_Resolution excluded.
            before_gets = h.get_ad_variant_image.base_call_count
            before_downloads = h.download.call_count
            try:
                asyncio.run(
                    jrs._run_edit_ad_variant_image_pipeline(
                        FakeTask(task_id=_TASK_ID, retries=attempt), _TASK_ID, **_PIPELINE_KWARGS
                    )
                )
                outcomes.append(None)
            except Exception as exc:  # noqa: BLE001 - classified below
                outcomes.append(exc)
            # One fresh fetch and one download per attempt, from that attempt's URL.
            assert h.get_ad_variant_image.base_call_count == before_gets + 1
            assert str(
                h.get_ad_variant_image.base_calls[-1].arguments["id_base_image"]
            ) == _ID_BASE_IMAGE
            assert h.download.call_count == before_downloads + 1
            assert h.download.urls[-1] == h.get_ad_variant_image.returned_urls[-1]

    assert all(isinstance(e, BaseImageDownloadError) and e.retryable for e in outcomes[:k])
    assert outcomes[k] is None
    urls = h.get_ad_variant_image.returned_urls
    assert len(set(urls)) == k + 1  # every attempt got a distinct fresh URL
    assert h.download.urls == urls
    # The checkpoint is written once (first attempt) and never with a signed URL.
    writes = h.redis.writes_for(fetch_key)
    assert len(writes) == 1
    assert writes[0].decoded["url"] not in urls
    assert h.edit.call_count == 1


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ad-variant-image-edit pipeline property tests passed")
