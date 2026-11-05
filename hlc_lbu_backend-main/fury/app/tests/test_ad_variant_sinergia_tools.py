"""Tests for the ad-variant Sinergia client (agents.tools.campaign_tools) and its mock.

Covers `get_ad_variant_image`, `upload_image_to_library` and
`_ad_variant_base_path`: exact path, request body, exception handling, DEBUG
logs free of image content and `inspect.signature` parity with Mock_Sinergia
(Req 4.1, 4.2, 4.4, 9.1, 9.2, 9.3, 12.9, 13.18, 13.29).

`_sinergia_get` / `_sinergia_post` are patched with recording fakes and every
test runs under `network_guard()`, so no real network call can happen.

Runnable two ways:
    python -m tests.test_ad_variant_sinergia_tools
    pytest tests/test_ad_variant_sinergia_tools.py
"""

from __future__ import annotations

import asyncio
import inspect
from contextlib import contextmanager
from typing import Any, Iterator

import httpx

from agents.tools import campaign_tools, mock_sinergia
from tests._edit_pipeline_fakes import LogCapture, network_guard, signed_url

BRAND_ID, CAMPAIGN_ID, AD_ID, CHANNEL_ID, VARIANT_ID = 11, 22, 33, 44, 55
IMAGE_NAME = "hero-banner"
ID_BASE_IMAGE = "img-abc-123"
BASE_PATH = (
    f"/api/v2/service/hiluca/brand/{BRAND_ID}/campaign/{CAMPAIGN_ID}"
    f"/ad/{AD_ID}/channel/{CHANNEL_ID}/variant/{VARIANT_ID}"
)
IDS = (BRAND_ID, CAMPAIGN_ID, AD_ID, CHANNEL_ID, VARIANT_ID)


class _RecordingHelper:
    """Async stand-in for `_sinergia_get` / `_sinergia_post` that records calls."""

    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.calls: list[tuple[tuple, dict]] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


@contextmanager
def _patched(**helpers: _RecordingHelper) -> Iterator[None]:
    """Replace `campaign_tools.<name>` for the context, under network_guard()."""
    originals = {name: getattr(campaign_tools, name) for name in helpers}
    try:
        for name, fake in helpers.items():
            setattr(campaign_tools, name, fake)
        with network_guard():
            yield
    finally:
        for name, orig in originals.items():
            setattr(campaign_tools, name, orig)


def _run(coro):
    return asyncio.run(coro)


def _raises(coro, exc_type: type[BaseException]) -> BaseException:
    try:
        result = _run(coro)
    except exc_type as exc:  # expected
        return exc
    raise AssertionError(f"expected {exc_type.__name__}, got return value {result!r}")


def _http_status_error(status: int = 500) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://sinergia.test/x")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError(f"{status}", request=request, response=response)


def _get(**kw):
    return campaign_tools.get_ad_variant_image(*IDS, IMAGE_NAME, ID_BASE_IMAGE, **kw)




# ── _ad_variant_base_path ───────────────────────────────────────────────────


def test_base_path_is_exact():
    assert campaign_tools._ad_variant_base_path(*IDS) == BASE_PATH


# ── get_ad_variant_image ────────────────────────────────────────────────────


def test_get_calls_sinergia_get_once_with_exact_path():
    fake_get = _RecordingHelper({"data": {"id": ID_BASE_IMAGE, "url": "https://x/a.png", "prompt": "p"}})
    fake_post = _RecordingHelper(AssertionError("_sinergia_post must not be called"))
    with _patched(_sinergia_get=fake_get, _sinergia_post=fake_post):
        result = _run(_get())
    assert len(fake_get.calls) == 1
    assert fake_post.calls == []
    args, kwargs = fake_get.calls[0]
    path = args[0] if args else kwargs["path"]
    assert path == f"{BASE_PATH}/image/{ID_BASE_IMAGE}"
    assert result == {"id": ID_BASE_IMAGE, "url": "https://x/a.png", "prompt": "p"}


def test_get_propagates_http_status_error():
    fake_get = _RecordingHelper(_http_status_error(503))
    with _patched(_sinergia_get=fake_get):
        _raises(_get(), httpx.HTTPStatusError)
    assert len(fake_get.calls) == 1


def test_get_propagates_timeout_and_network_errors():
    for exc in (
        httpx.ReadTimeout("timeout"),
        httpx.ConnectError("refused"),
    ):
        fake_get = _RecordingHelper(exc)
        with _patched(_sinergia_get=fake_get):
            raised = _raises(_get(), type(exc))
        assert raised is exc


def test_get_raises_on_non_dict_body_instead_of_returning_empty():
    for body in ([], None, "oops"):
        with _patched(_sinergia_get=_RecordingHelper(body)):
            _raises(_get(), ValueError)


# ── upload_image_to_library ─────────────────────────────────────────────────
LIBRARY_UPLOAD_PATH = f"/api/v2/service/hiluca/ad/{AD_ID}/image/upload"
_B64_PAYLOAD = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
DATA_URI = f"data:image/png;base64,{_B64_PAYLOAD}"
def _library_payload(image_data: str = DATA_URI) -> dict:
    return {"image_data": image_data, "image_name": f"{IMAGE_NAME}_1", "mime_type": "image/png"}
def _library_upload(image_data: dict):
    return campaign_tools.upload_image_to_library(AD_ID, image_data)
def test_library_upload_posts_exact_path_and_body_and_returns_image_id():
    payload = _library_payload()
    fake_post = _RecordingHelper({"data": {"image_id": "new-1", "url": "https://x/new-1.png"}})
    fake_get = _RecordingHelper(AssertionError("_sinergia_get must not be called"))
    with _patched(_sinergia_post=fake_post, _sinergia_get=fake_get):
        result = _run(_library_upload(payload))
    assert len(fake_post.calls) == 1
    assert fake_get.calls == []
    args, kwargs = fake_post.calls[0]
    path = args[0] if args else kwargs["path"]
    body = args[1] if len(args) > 1 else kwargs["body"]
    assert path == LIBRARY_UPLOAD_PATH
    assert body == {"image": payload}
    assert result == "new-1"
def test_library_upload_returns_empty_without_image_id():
    for body in ({"data": {"url": "https://x/a.png"}}, {"data": {}}, {}):
        with _patched(_sinergia_post=_RecordingHelper(body)):
            assert _run(_library_upload(_library_payload())) == ""
def test_library_upload_returns_empty_when_post_raises():
    for exc in (_http_status_error(500), httpx.ReadTimeout("timeout"), httpx.ConnectError("down")):
        fake_post = _RecordingHelper(exc)
        with _patched(_sinergia_post=fake_post):
            assert _run(_library_upload(_library_payload())) == ""
        assert len(fake_post.calls) == 1
def test_library_upload_debug_log_has_no_image_content():
    """Req 12.9, 13.29: no captured line (DEBUG included) leaks base64 or signature params."""
    url = signed_url("variant.png", 7)
    cases = (
        (DATA_URI, (_B64_PAYLOAD, _B64_PAYLOAD[:16]), "data-uri:image/png"),
        (url, ("X-Amz-Signature", "X-Amz-Credential", "fakesig7"), "url len="),
    )
    for image_data, forbidden, descriptor in cases:
        for outcome in ({"data": {"image_id": "new-1"}}, httpx.ConnectError("down")):
            with LogCapture() as cap, _patched(_sinergia_post=_RecordingHelper(outcome)):
                result = _run(_library_upload(_library_payload(image_data)))
            assert result == ("new-1" if isinstance(outcome, dict) else "")
            debug = [r.message for r in cap.records if r.level == "DEBUG"]
            assert any(descriptor in line for line in debug), debug
            for line in cap.lines:
                for secret in forbidden:
                    assert secret not in line, (secret, line)
# ── Mock_Sinergia signature parity (Req 13.18) ──────────────────────────────


def test_mock_signatures_match_real_client():
    for name in ("get_ad_variant_image", "upload_image_to_library"):
        real = getattr(campaign_tools, name)
        mock = getattr(mock_sinergia, name)
        assert inspect.iscoroutinefunction(real) and inspect.iscoroutinefunction(mock), name
        assert inspect.signature(mock) == inspect.signature(real), name
    for module in (campaign_tools, mock_sinergia):
        assert not hasattr(module, "upload_ad_variant_image_from_edit"), module.__name__


def test_real_signatures_match_contract():
    get_params = list(inspect.signature(campaign_tools.get_ad_variant_image).parameters)
    assert get_params == [
        "brand_id", "campaign_id", "ad_id", "channel_id", "variant_id",
        "image_name", "id_base_image",
    ]
    up_params = list(inspect.signature(campaign_tools.upload_image_to_library).parameters)
    assert up_params == ["ad_id", "image_data"]


# ── Property-based tests ────────────────────────────────────────────────────

from hypothesis import given, settings, strategies as st  # noqa: E402

_ABSENT = object()
_RESERVED_KEYS = {"id", "url", "prompt", "image_id", "data"}
_field = st.one_of(st.just(_ABSENT), st.none(), st.text(max_size=40))
_extra_keys = st.dictionaries(
    st.text(min_size=1, max_size=12).filter(lambda k: k not in _RESERVED_KEYS),
    st.one_of(st.none(), st.integers(), st.text(max_size=10), st.booleans()),
    max_size=4,
)


def _build_body(fields: dict[str, Any], extras: dict, wrap: bool) -> dict:
    data = dict(extras)
    data.update({k: v for k, v in fields.items() if v is not _ABSENT})
    return {"data": data, "status": "ok"} if wrap else data


def _expected(value: Any) -> str:
    return "" if value is _ABSENT or value is None else value


# Feature: ad-variant-image-edit-pipeline, Property 6: El cliente de Sinergia normaliza la respuesta
@settings(max_examples=100, deadline=None)
@given(
    id_=_field, url=_field, prompt=_field,
    extras=_extra_keys, wrap=st.booleans(),
)
def test_property_6_get_normalizes_response(id_, url, prompt, extras, wrap):
    """**Validates: Requirements 4.3**"""
    body = _build_body({"id": id_, "url": url, "prompt": prompt}, extras, wrap)
    with _patched(_sinergia_get=_RecordingHelper(body)):
        result = _run(_get())
    assert set(result) == {"id", "url", "prompt"}
    assert all(isinstance(v, str) for v in result.values())
    assert result == {"id": _expected(id_), "url": _expected(url), "prompt": _expected(prompt)}


_pos_int = st.integers(min_value=1, max_value=10**9)
_ids_tuple = st.tuples(_pos_int, _pos_int, _pos_int, _pos_int, _pos_int)
_nonempty_text = st.text(min_size=1, max_size=40)
# image_ids produced by the upload mock across ALL examples of this process.
_seen_mock_upload_ids: set[str] = set()


# Feature: ad-variant-image-edit-pipeline, Property 7: Mocks de Sinergia deterministas y únicos
@settings(max_examples=100, deadline=None)
@given(ids=_ids_tuple, image_name=_nonempty_text, id_base_image=_nonempty_text)
def test_property_7_mock_get_is_deterministic(ids, image_name, id_base_image):
    """**Validates: Requirements 4.6, 9.6**"""
    with network_guard():
        first = _run(mock_sinergia.get_ad_variant_image(*ids, image_name, id_base_image))
        second = _run(mock_sinergia.get_ad_variant_image(*ids, image_name, id_base_image))
    assert first == second
    assert first["id"] == id_base_image
    assert isinstance(first["url"], str) and first["url"]


# Feature: ad-variant-image-edit-pipeline, Property 7: Mocks de Sinergia deterministas y únicos
@settings(max_examples=100, deadline=None)
@given(
    ad_id=_pos_int,
    k=st.integers(min_value=1, max_value=20),
    image_data=st.fixed_dictionaries({
        "image_data": st.text(max_size=40),
        "image_name": _nonempty_text,
        "mime_type": st.sampled_from(["image/png", "image/jpeg", "image/webp"]),
    }),
)
def test_property_7_mock_upload_ids_unique(ad_id, k, image_data):
    """**Validates: Requirements 4.6, 9.6, 14.13**"""
    async def _upload_k() -> list[str]:
        return [
            await mock_sinergia.upload_image_to_library(ad_id, image_data)
            for _ in range(k)
        ]

    with network_guard():
        image_ids = _run(_upload_k())
    assert len(image_ids) == k
    assert all(isinstance(i, str) and i for i in image_ids)
    assert len(set(image_ids)) == k
    # Uniqueness holds process-wide, not just within one batch.
    assert _seen_mock_upload_ids.isdisjoint(image_ids)
    _seen_mock_upload_ids.update(image_ids)


_B64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_WINDOW = 16
# image_id alphabet disjoint from base64/hex so the logged response can never
# accidentally contain a forbidden substring.
_image_id = st.text(alphabet="-_.~:", min_size=1, max_size=20)
_sig_value = st.text(alphabet="0123456789abcdef", min_size=_WINDOW, max_size=40)
_amz_suffix = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=1, max_size=12)


@st.composite
def _image_payload(draw) -> tuple[str, list[str], str]:
    """(image_data, forbidden substrings, expected DEBUG descriptor prefix)."""
    kind = draw(st.sampled_from(["data-uri", "signed-url", "text"]))
    if kind == "data-uri":
        body = draw(st.text(alphabet=_B64_ALPHABET, min_size=1, max_size=5000))
        body += "=" * draw(st.integers(min_value=0, max_value=2))
        mime = draw(st.sampled_from(["image/png", "image/jpeg", "image/webp"]))
        windows = sorted({body[i:i + _WINDOW] for i in range(len(body) - _WINDOW + 1)})
        return f"data:{mime};base64,{body}", windows, f"data-uri:{mime} len="
    if kind == "signed-url":
        params = draw(st.dictionaries(_amz_suffix, _sig_value, min_size=1, max_size=6))
        params.setdefault("Signature", draw(_sig_value))
        query = "&".join(f"X-Amz-{k}={v}" for k, v in params.items())
        path = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=12))
        url = f"https://bucket.s3.amazonaws.com/{path}.png?{query}"
        return url, list(params.values()), "url len="
    text = draw(st.text(min_size=1, max_size=200).filter(
        lambda t: not t[:5].lower().startswith("data:") and not t[:8].lower().startswith(("http://", "https://"))
    ))
    return text, [], "text len="


_post_outcome = st.one_of(
    _image_id.map(lambda i: ("ok", {"data": {"image_id": i, "url": "https://x/new.png"}}, i)),
    st.sampled_from([{"data": {}}, {}, {"data": {"url": "https://x/a.png"}}, {"data": {"image_id": ""}}])
      .map(lambda b: ("missing", b, "")),
    st.sampled_from(["http", "timeout", "connect"]).map(lambda k: ("raise", k, "")),
)


def _make_exc(kind: str) -> BaseException:
    if kind == "http":
        return _http_status_error(500)
    if kind == "timeout":
        return httpx.ReadTimeout("timeout")
    return httpx.ConnectError("down")


def _windows(line: str) -> set[str]:
    return {line[i:i + _WINDOW] for i in range(len(line) - _WINDOW + 1)}


# Feature: ad-variant-image-edit-pipeline, Property 21: El log de `upload_image_to_library` no filtra contenido
@settings(max_examples=100, deadline=None)
@given(ad_id=_pos_int, payload=_image_payload(), outcome=_post_outcome)
def test_property_21_library_upload_log_has_no_content(ad_id, payload, outcome):
    """**Validates: Requirements 9.2, 9.3, 12.9, 13.29**"""
    image_data, forbidden, descriptor = payload
    kind, value, expected = outcome
    fake_post = _RecordingHelper(_make_exc(value) if kind == "raise" else value)
    body = {"image_data": image_data, "image_name": f"{IMAGE_NAME}_1", "mime_type": "image/png"}
    with LogCapture(level="DEBUG") as cap, _patched(_sinergia_post=fake_post):
        result = _run(campaign_tools.upload_image_to_library(ad_id, body))

    # Existing contract intact.
    assert result == expected
    assert len(fake_post.calls) == 1
    debug = cap.at_level("DEBUG")
    assert any(descriptor in line for line in debug), debug

    forbidden_set = set(forbidden)
    for line in cap.lines:
        if descriptor.startswith("data-uri"):
            assert not (_windows(line) & forbidden_set), line
        else:
            for secret in forbidden:
                assert secret not in line, (secret, line)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ad-variant sinergia tools tests passed")
