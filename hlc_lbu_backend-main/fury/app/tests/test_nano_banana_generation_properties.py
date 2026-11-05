"""Property-based tests for `agents.nano_banana_agent.generate_images_from_prompts`
(adset-creative-diversity, Image_Generator).

Everything runs in memory: `google.genai.Client`, `httpx.get` and the Upload_Tool
are replaced by the shared fakes in tests/_diversity_pipeline_fakes.py and any
real outbound call fails through `network_guard()`.

The strategies below (`image_prompt_values`, `gemini_outcomes`, `prompt_items`,
`prompt_data_lists`, `generation_scenarios`) and the `run_generation` helper are
meant to be reused by the other Image_Generator properties of this file.
"""
from __future__ import annotations

import asyncio
import base64
import copy
from contextlib import ExitStack
from dataclasses import dataclass, field
from typing import Any

import httpx
from google import genai
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from agents import nano_banana_agent
from core.config import settings
from tests._diversity_pipeline_fakes import (
    DEFAULT,
    AttrPatcher,
    FakeHttpResponse,
    FakeGenaiClientFactory,
    FakeHttpxGet,
    FakeUploadImageToLibraryTool,
    SettingsPatcher,
    make_genai_empty_response,
    make_genai_image_response,
    make_genai_text_response,
    network_guard,
)

UPLOAD_KEYS = {"image_data", "image_name", "mime_type", "plan_id", "image_prompt"}

# Marker for "the item has no `image_prompt` key at all".
ABSENT = object()


# ---------------------------------------------------------------------------
# Strategies (reusable)
# ---------------------------------------------------------------------------

_json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-10**6, max_value=10**6),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=10),
)

# Values for `item["image_prompt"]`: str, absent, None, numbers and objects.
image_prompt_values = st.one_of(
    st.text(max_size=60),
    st.just(ABSENT),
    st.none(),
    st.integers(min_value=-10**6, max_value=10**6),
    st.floats(allow_nan=False, allow_infinity=False),
    st.dictionaries(st.text(max_size=5), _json_scalars, max_size=3),
    st.lists(_json_scalars, max_size=3),
)

_image_mime_types = st.sampled_from(["image/png", "image/jpeg", "image/webp"])

# One Gemini_Image_Call outcome: an image (success) or a failure of any kind.
gemini_outcomes = st.one_of(
    st.builds(
        make_genai_image_response,
        data=st.binary(min_size=1, max_size=32),
        mime_type=_image_mime_types,
    ),
    st.builds(make_genai_text_response, text=st.text(max_size=10)),
    st.builds(make_genai_empty_response),
    st.sampled_from([ValueError("gen failed"), asyncio.TimeoutError(), RuntimeError("boom")]),
)


@st.composite
def prompt_items(draw, element_id: str) -> dict[str, Any]:
    """One element of `image_prompts` as produced by the Image_Prompter."""
    item: dict[str, Any] = {"element_id": element_id}
    value = draw(image_prompt_values)
    if value is not ABSENT:
        item["image_prompt"] = value
    if draw(st.booleans()):
        item["image_request"] = {
            "technical_specs": {"aspect_ratio": draw(st.sampled_from(["9:16", "4:5", "1:1"]))}
        }
    return item


@st.composite
def prompt_data_lists(draw, max_prompts: int = 3, max_items: int = 3) -> list[dict[str, Any]]:
    """`image_prompts` argument: list of prompt_data dicts with unique element_ids.

    Covers the text-only path and the product/base image path (where a non-str
    `image_prompt` still reaches Gemini through an f-string), and Diversity_Path
    prompts carrying `variant_key`.
    """
    n_prompts = draw(st.integers(min_value=1, max_value=max_prompts))
    prompts: list[dict[str, Any]] = []
    for p in range(n_prompts):
        n_items = draw(st.integers(min_value=0, max_value=max_items))
        data: dict[str, Any] = {
            "plan_id": draw(st.sampled_from([f"plan_{p}", f"P{p}", ""])),
            "image_prompts": [draw(prompt_items(f"el_{p}_{i}")) for i in range(n_items)],
        }
        if draw(st.booleans()):
            data["base_image_url"] = f"https://bucket.example/base_{p}.png?sig=s{p}"
        if draw(st.booleans()):
            data["product_image_urls"] = [
                f"https://bucket.example/prod_{p}_{k}.jpg?sig=s{k}"
                for k in range(draw(st.integers(min_value=1, max_value=2)))
            ]
        if draw(st.booleans()):
            data["variant_key"] = f"vk_{p}"
        prompts.append(data)
    return prompts


@dataclass
class GenerationScenario:
    prompts: list[dict[str, Any]]
    gemini_script: list[Any]
    diversity_flag: bool
    ad_id: Any = 7


@st.composite
def generation_scenarios(draw, **kwargs: Any) -> GenerationScenario:
    prompts = draw(prompt_data_lists(**kwargs))
    n_items = sum(len(p["image_prompts"]) for p in prompts)
    script = draw(st.lists(gemini_outcomes, min_size=n_items, max_size=n_items))
    return GenerationScenario(
        prompts=prompts,
        gemini_script=script,
        diversity_flag=draw(st.booleans()),
        ad_id=draw(st.sampled_from([7, "42", 1001])),
    )


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

class SnapshotUploadTool(FakeUploadImageToLibraryTool):
    """Upload_Tool fake that deep-copies `image_data` at call time (the
    Image_Generator adds `image_id` to the same dict after the upload)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.snapshots: list[dict[str, Any]] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.snapshots.append(copy.deepcopy(self._bind(args, kwargs).get("image_data")))
        return await super().__call__(*args, **kwargs)


@dataclass
class GenerationRun:
    result: dict[str, Any]
    genai: FakeGenaiClientFactory
    httpx_get: FakeHttpxGet
    upload: SnapshotUploadTool
    original_prompts: list[dict[str, Any]] = field(default_factory=list)


def run_generation(
    scenario: GenerationScenario,
    *,
    upload_image_to_library: bool = True,
    genai_factory: FakeGenaiClientFactory | None = None,
    httpx_get: FakeHttpxGet | None = None,
    upload: SnapshotUploadTool | None = None,
) -> GenerationRun:
    """Run `generate_images_from_prompts` on a deep copy of the scenario prompts."""
    genai_factory = genai_factory or FakeGenaiClientFactory(script=list(scenario.gemini_script))
    httpx_get = httpx_get or FakeHttpxGet()
    upload = upload or SnapshotUploadTool()
    original = copy.deepcopy(scenario.prompts)
    prompts = copy.deepcopy(scenario.prompts)

    patcher = AttrPatcher()
    sp = SettingsPatcher(settings)
    with ExitStack() as stack:
        stack.callback(patcher.undo)
        stack.callback(sp.undo)
        stack.enter_context(network_guard())
        patcher.set(genai, "Client", genai_factory)
        patcher.set(httpx, "get", httpx_get)
        patcher.set(nano_banana_agent, "upload_image_to_library_tool", upload)
        sp.set("USE_ADSET_CREATIVE_DIVERSITY", scenario.diversity_flag)
        result = asyncio.run(
            nano_banana_agent.generate_images_from_prompts(
                prompts, scenario.ad_id, upload_image_to_library=upload_image_to_library
            )
        )
    return GenerationRun(result, genai_factory, httpx_get, upload, original)


def expected_image_prompt(item: dict[str, Any]) -> str:
    value = item.get("image_prompt")
    return value if isinstance(value, str) else ""


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

# Feature: adset-creative-diversity, Property 19: image_prompt en el payload de subida
@h_settings(max_examples=100, deadline=None)
@given(scenario=generation_scenarios())
def test_upload_payload_carries_image_prompt(scenario: GenerationScenario) -> None:
    """**Validates: Requirements 9.1, 9.2, 9.6, 11.5**"""
    run = run_generation(scenario)
    originals = {
        item["element_id"]: item
        for p in run.original_prompts
        for item in p["image_prompts"]
    }

    expected: list[dict[str, Any]] = []
    for g in run.result["generated_images"]:
        for item in g.get("image_prompts", []):
            if item.get("image_url"):
                expected.append({
                    "image_data": item["image_url"],
                    "image_name": item["element_id"],
                    "mime_type": item.get("image_mime_type"),
                    "plan_id": g.get("plan_id"),
                    "image_prompt": expected_image_prompt(originals[item["element_id"]]),
                })

    uploads = run.upload.snapshots
    # exactly the five keys on every payload
    for payload in uploads:
        assert set(payload) == UPLOAD_KEYS
        assert isinstance(payload["image_prompt"], str)
    # one upload per element with a non-empty image_url, none for failed ones
    assert uploads == expected
    assert len(uploads) == len({u["image_name"] for u in uploads})
    # every generated image actually went through the Upload_Tool, with the ad id
    assert all(c.arguments.get("ad_id") == scenario.ad_id for c in run.upload.calls)
    # the prompt text itself is never altered in the generated output
    for g in run.result["generated_images"]:
        for item in g.get("image_prompts", []):
            orig = originals[item["element_id"]]
            assert ("image_prompt" in item) == ("image_prompt" in orig)
            if "image_prompt" in orig:
                assert item["image_prompt"] == orig["image_prompt"]


_hex16 = st.text(alphabet="0123456789abcdef", min_size=16, max_size=16)


@dataclass
class SecretScenario:
    scenario: GenerationScenario
    client_script: list[Any]
    download_by_url: dict[str, list[Any]]
    upload_script: list[Any]
    signatures: list[str]
    api_key: str
    b64_fragment: str
    prompt_markers: list[str]
    image_b64s: list[str]
    error_names: set[str]


@st.composite
def secret_scenarios(draw) -> SecretScenario:
    """generation_scenarios() enriched with secrets: signed URLs, exceptions whose
    messages carry those URLs + an API key + base64, marker texts in image_prompt."""
    base = draw(generation_scenarios())
    api_key = "AIzaSy" + draw(_hex16)
    b64_fragment = base64.b64encode(
        draw(st.binary(min_size=12, max_size=24)) + b"\x00secret"
    ).decode()
    signatures: list[str] = []
    prompt_markers: list[str] = []
    error_names: set[str] = {"NoImageInResponse"}

    def secret_exc(url: str = "") -> BaseException:
        cls = draw(st.sampled_from([ValueError, RuntimeError, ConnectionError, KeyError]))
        error_names.add(cls.__name__)
        return cls(f"failed {url} key={api_key} payload={b64_fragment}")

    prompts = copy.deepcopy(base.prompts)
    download_by_url: dict[str, list[Any]] = {}
    for p in prompts:
        n_items = len(p["image_prompts"])
        url_keys = [k for k in ("base_image_url",) if k in p]
        for k in url_keys:
            sig = "SIG" + draw(_hex16)
            signatures.append(sig)
            p[k] = f"{p[k].partition('?')[0]}?X-Amz-Signature={sig}&X-Amz-Credential={api_key}"
        if "product_image_urls" in p:
            new_urls = []
            for u in p["product_image_urls"]:
                sig = "SIG" + draw(_hex16)
                signatures.append(sig)
                new_urls.append(f"{u.partition('?')[0]}?X-Amz-Signature={sig}&token={api_key}")
            p["product_image_urls"] = new_urls
        all_urls = ([p["base_image_url"]] if "base_image_url" in p else []) + list(
            p.get("product_image_urls", [])
        )
        for url in all_urls:
            outcomes = []
            for _ in range(n_items):
                kind = draw(st.sampled_from(["ok", "exc", "status", "empty"]))
                if kind == "ok":
                    outcomes.append(FakeHttpResponse())
                elif kind == "exc":
                    outcomes.append(secret_exc(url))
                elif kind == "status":
                    outcomes.append(FakeHttpResponse(status_code=403, content=f"denied {url}".encode()))
                else:
                    outcomes.append(FakeHttpResponse(content=b""))
            download_by_url[url] = outcomes
        for item in p["image_prompts"]:
            marker = "PROMPTMARK" + draw(_hex16)
            prompt_markers.append(marker)
            shape = draw(st.sampled_from(["str", "dict"]))
            item["image_prompt"] = (
                f"scene with {marker} lighting" if shape == "str" else {"text": marker}
            )

    all_urls = list(download_by_url) or [""]
    gemini_script: list[Any] = []
    image_b64s: list[str] = []
    for _ in base.gemini_script:
        kind = draw(st.sampled_from(["image", "text", "empty", "exc", "timeout"]))
        if kind == "image":
            data = draw(st.binary(min_size=12, max_size=32))
            image_b64s.append(base64.b64encode(data).decode())
            gemini_script.append(make_genai_image_response(data=data))
        elif kind == "text":
            gemini_script.append(make_genai_text_response(text=f"no image {api_key}"))
        elif kind == "empty":
            gemini_script.append(make_genai_empty_response())
        elif kind == "exc":
            gemini_script.append(secret_exc(draw(st.sampled_from(all_urls))))
        else:
            error_names.add("TimeoutError")
            gemini_script.append(asyncio.TimeoutError(f"timeout {api_key}"))

    client_script = [
        secret_exc() if draw(st.booleans()) and draw(st.booleans()) else DEFAULT
        for _ in prompts
    ]
    n_items_total = sum(len(p["image_prompts"]) for p in prompts)
    upload_script = [
        draw(st.sampled_from(["default", "empty", "exc"])) for _ in range(n_items_total)
    ]
    upload_script = [
        DEFAULT if u == "default" else "" if u == "empty" else secret_exc() for u in upload_script
    ]
    scenario = GenerationScenario(
        prompts=prompts,
        gemini_script=gemini_script,
        diversity_flag=base.diversity_flag,
        ad_id=base.ad_id,
    )
    return SecretScenario(
        scenario, client_script, download_by_url, upload_script, signatures, api_key,
        b64_fragment, prompt_markers, image_b64s, error_names,
    )


def capture_logs(fn: Any) -> tuple[Any, list[str]]:
    """Run `fn()` with a loguru sink capturing every formatted line (incl. tracebacks)."""
    from loguru import logger as loguru_logger

    lines: list[str] = []
    sink_id = loguru_logger.add(lambda m: lines.append(str(m)), level=0, format="{level}|{message}")
    try:
        return fn(), lines
    finally:
        loguru_logger.remove(sink_id)


# Feature: adset-creative-diversity, Property 20: Logs y errores sin secretos ni binarios
@h_settings(max_examples=100, deadline=None)
@given(secret=secret_scenarios())
def test_logs_and_errors_carry_no_secrets(secret: SecretScenario) -> None:
    """**Validates: Requirements 9.7, 11.8**"""
    run, lines = capture_logs(lambda: run_generation(
        secret.scenario,
        genai_factory=FakeGenaiClientFactory(
            script=list(secret.scenario.gemini_script), client_script=list(secret.client_script)
        ),
        httpx_get=FakeHttpxGet(by_url=copy.deepcopy(secret.download_by_url)),
        upload=SnapshotUploadTool(script=list(secret.upload_script)),
    ))

    forbidden = (
        ["X-Amz-Signature", "X-Amz-Credential", "token=", secret.api_key, secret.b64_fragment]
        + secret.signatures
        + secret.prompt_markers
        + secret.image_b64s
    )
    errors: list[str] = []
    for g in run.result["generated_images"]:
        if "error" in g:
            errors.append(str(g["error"]))
        for item in g.get("image_prompts", []):
            if "image_error" in item:
                errors.append(str(item["image_error"]))

    # Non-str image_prompt on the text-only path is rejected by Part.from_text (pydantic)
    # before the Gemini call: that class name is also a legitimate image_error.
    allowed_errors = secret.error_names | {"ValidationError"}

    assert lines, "the Image_Generator logged nothing"
    for line in lines:
        for secret_text in forbidden:
            assert secret_text not in line, f"secret {secret_text!r} leaked in log: {line!r}"
    for err in errors:
        # only exception class names or "NoImageInResponse"
        assert err in allowed_errors, f"unexpected error value {err!r}"
        for secret_text in forbidden:
            assert secret_text not in err


DOWNLOAD_KINDS = ("ok", "exception", "timeout", "status", "empty")


@dataclass
class DownloadScenario:
    scenario: GenerationScenario
    download_by_url: dict[str, list[Any]]
    # (prompt index, item index) -> ordered bytes of the successful downloads
    expected_images: dict[tuple[int, int], list[bytes]]
    n_failed: int
    n_downloads: int


def _download_outcome(kind: str, payload: bytes, status: int) -> Any:
    if kind == "ok":
        return FakeHttpResponse(content=payload)
    if kind == "exception":
        return ConnectionError("connection reset")
    if kind == "timeout":
        return httpx.ReadTimeout("read timed out")
    if kind == "status":
        return FakeHttpResponse(status_code=status, content=b"not an image")
    return FakeHttpResponse(content=b"")


@st.composite
def download_scenarios(draw) -> DownloadScenario:
    """Prompts with optional `base_image_url` and 0..3 `product_image_urls` (all URLs
    distinct), and one download outcome per (URL, element). `image_prompt` is always a
    str carrying a unique marker so each Gemini call can be matched to its element."""
    n_prompts = draw(st.integers(min_value=1, max_value=3))
    prompts: list[dict[str, Any]] = []
    by_url: dict[str, list[Any]] = {}
    expected: dict[tuple[int, int], list[bytes]] = {}
    n_failed = n_downloads = 0
    for p in range(n_prompts):
        n_items = draw(st.integers(min_value=0, max_value=3))
        data: dict[str, Any] = {
            "plan_id": f"plan_{p}",
            "image_prompts": [
                {"element_id": f"el_{p}_{i}", "image_prompt": f"scene MARK_{p}_{i}"}
                for i in range(n_items)
            ],
        }
        urls: list[str] = []
        if draw(st.booleans()):
            data["base_image_url"] = f"https://bucket.example/base_{p}.png?sig=b{p}"
            urls.append(data["base_image_url"])
        n_products = draw(st.integers(min_value=0, max_value=3))
        if n_products or draw(st.booleans()):
            data["product_image_urls"] = [
                f"https://bucket.example/prod_{p}_{k}.jpg?sig=p{k}" for k in range(n_products)
            ]
            urls.extend(data["product_image_urls"])
        for i in range(n_items):
            expected[(p, i)] = []
        for u, url in enumerate(urls):
            outcomes = []
            for i in range(n_items):
                kind = draw(st.sampled_from(DOWNLOAD_KINDS))
                status = draw(st.sampled_from([201, 204, 301, 403, 404, 500]))
                payload = f"IMG|{p}|{u}|{i}".encode()
                outcomes.append(_download_outcome(kind, payload, status))
                n_downloads += 1
                if kind == "ok":
                    expected[(p, i)].append(payload)
                else:
                    n_failed += 1
            by_url[url] = outcomes
        prompts.append(data)
    scenario = GenerationScenario(
        prompts=prompts,
        gemini_script=[],  # every Gemini call returns an image
        diversity_flag=draw(st.booleans()),
        ad_id=draw(st.sampled_from([7, "42", 1001])),
    )
    return DownloadScenario(scenario, by_url, expected, n_failed, n_downloads)


# Feature: adset-creative-diversity, Property 21: Resiliencia ante descargas fallidas
@h_settings(max_examples=100, deadline=None)
@given(dl=download_scenarios())
def test_failed_downloads_are_skipped_and_generation_continues(dl: DownloadScenario) -> None:
    """**Validates: Requirements 11.1, 11.2**"""
    genai_factory = FakeGenaiClientFactory()
    run, lines = capture_logs(lambda: run_generation(
        dl.scenario,
        genai_factory=genai_factory,
        httpx_get=FakeHttpxGet(by_url=dl.download_by_url),
    ))

    # every planned download was attempted (one per URL per element)
    assert run.httpx_get.call_count == dl.n_downloads

    # exactly one Gemini_Image_Call per element
    calls_by_marker: dict[tuple[int, int], list[list[Any]]] = {}
    for call in genai_factory.generate_calls:
        contents = call["kwargs"]["contents"]
        text = contents[-1].text
        assert isinstance(text, str)
        marker = text.split("MARK_", 1)[1].split()[0]
        p, i = (int(x) for x in marker.split("_"))
        calls_by_marker.setdefault((p, i), []).append(contents)
    assert set(calls_by_marker) == set(dl.expected_images)
    assert all(len(v) == 1 for v in calls_by_marker.values())

    for key, payloads in dl.expected_images.items():
        contents = calls_by_marker[key][0]
        # image parts of the successful downloads (in order) + the text part last
        image_parts, text_part = contents[:-1], contents[-1]
        assert [part.inline_data.data for part in image_parts] == payloads
        assert text_part.inline_data is None
        assert f"MARK_{key[0]}_{key[1]}" in text_part.text

    # one warning per failed download
    download_warnings = [
        line for line in lines
        if line.startswith("WARNING|")
        and ("failed to download" in line or "empty image bytes" in line)
    ]
    assert len(download_warnings) == dl.n_failed

    # every element continued its generation and got its image
    for g in run.result["generated_images"]:
        for item in g.get("image_prompts", []):
            assert item.get("image_url")
            assert "image_error" not in item


class CustomGeminiError(Exception):
    """Arbitrary user-defined exception class raised by the Gemini_Image_Call."""


# Gemini outcome kinds of Property 22 and the image_error each one must produce.
FAILURE_KINDS = ("exception", "timeout", "no_candidates", "no_inline_data")
_exception_classes = st.sampled_from(
    [ValueError, RuntimeError, ConnectionError, KeyError, OSError, CustomGeminiError]
)


@dataclass
class FailureScenario:
    scenario: GenerationScenario
    # marker -> Gemini outcome for the element whose prompt carries that marker
    outcome_by_marker: dict[str, Any]
    # marker -> expected image_error (None for a success)
    expected_error: dict[str, str | None]
    # marker -> expected image_url (data URL) for successes
    expected_url: dict[str, str]
    # one Client(...) outcome per prompt (prompts run sequentially, concurrency 1)
    client_script: list[Any]


@st.composite
def failure_scenarios(draw) -> FailureScenario:
    """Prompts whose elements carry a unique marker in `image_prompt`; each element gets
    an image or one failure kind, and each prompt may fail at `gai.Client` creation."""
    n_prompts = draw(st.integers(min_value=1, max_value=3))
    prompts: list[dict[str, Any]] = []
    outcome_by_marker: dict[str, Any] = {}
    expected_error: dict[str, str | None] = {}
    expected_url: dict[str, str] = {}
    client_script: list[Any] = []
    for p in range(n_prompts):
        n_items = draw(st.integers(min_value=0, max_value=3))
        client_fails = draw(st.integers(min_value=0, max_value=3)) == 0
        client_exc_cls = draw(_exception_classes)
        client_script.append(client_exc_cls("client init failed") if client_fails else DEFAULT)
        items = []
        for i in range(n_items):
            marker = f"MARK_{p}_{i}"
            items.append({"element_id": f"el_{p}_{i}", "image_prompt": f"scene {marker} end"})
            kind = draw(st.sampled_from(("image",) + FAILURE_KINDS))
            if kind == "image":
                data = draw(st.binary(min_size=1, max_size=32))
                mime = draw(_image_mime_types)
                outcome: Any = make_genai_image_response(data=data, mime_type=mime)
                error = None
                expected_url[marker] = f"data:{mime};base64,{base64.b64encode(data).decode()}"
            elif kind == "exception":
                cls = draw(_exception_classes)
                outcome, error = cls("gen failed"), cls.__name__
            elif kind == "timeout":
                outcome, error = asyncio.TimeoutError(), "TimeoutError"
            elif kind == "no_candidates":
                outcome, error = make_genai_empty_response(), "NoImageInResponse"
            else:
                outcome = make_genai_text_response(text=draw(st.text(max_size=10)))
                error = "NoImageInResponse"
            if client_fails:
                # the Gemini call is never reached: every element gets the client error
                error = client_exc_cls.__name__
                expected_url.pop(marker, None)
            outcome_by_marker[marker] = outcome
            expected_error[marker] = error
        data_p: dict[str, Any] = {"plan_id": f"plan_{p}", "image_prompts": items}
        if draw(st.booleans()):
            data_p["product_image_urls"] = [f"https://bucket.example/prod_{p}.jpg?sig=s{p}"]
        if draw(st.booleans()):
            data_p["variant_key"] = f"vk_{p}"
        prompts.append(data_p)
    scenario = GenerationScenario(
        prompts=prompts,
        gemini_script=[],
        diversity_flag=draw(st.booleans()),
        ad_id=draw(st.sampled_from([7, "42", 1001])),
    )
    return FailureScenario(scenario, outcome_by_marker, expected_error, expected_url, client_script)


class MarkerKeyedGenaiFactory(FakeGenaiClientFactory):
    """Gemini fake whose outcome is chosen by the element marker found in the text part."""

    def __init__(self, outcome_by_marker: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.outcome_by_marker = outcome_by_marker
        self.markers_called: list[str] = []

    def _generate_content(self, *args: Any, **kwargs: Any) -> Any:
        text = kwargs["contents"][-1].text
        marker = "MARK_" + text.split("MARK_", 1)[1].split()[0]
        self.markers_called.append(marker)
        self.script = [self.outcome_by_marker[marker]]
        return super()._generate_content(*args, **kwargs)


# Feature: adset-creative-diversity, Property 22: Marcado de fallos de generación
@h_settings(max_examples=100, deadline=None)
@given(fs=failure_scenarios())
def test_generation_failures_are_marked_and_not_uploaded(fs: FailureScenario) -> None:
    """**Validates: Requirements 11.3, 11.4, 11.5**"""
    genai_factory = MarkerKeyedGenaiFactory(
        fs.outcome_by_marker, client_script=list(fs.client_script)
    )
    sp = SettingsPatcher(settings)
    try:
        # concurrency 1 → prompts run in order, so client_script maps 1:1 to prompts
        sp.set("IMAGE_GEN_MAX_CONCURRENCY", 1)
        # generate_images_from_prompts must not raise
        run = run_generation(fs.scenario, genai_factory=genai_factory)
    finally:
        sp.undo()

    assert run.result["ok"] is True
    generated = run.result["generated_images"]
    assert len(generated) == len(fs.scenario.prompts)

    # Gemini is only called for elements of prompts whose client was created
    expected_called = {
        m for m, err in fs.expected_error.items()
        if not (err and fs.client_script[int(m.split("_")[1])] is not DEFAULT)
    }
    assert sorted(genai_factory.markers_called) == sorted(expected_called)

    uploaded_names = {s["image_name"] for s in run.upload.snapshots}
    seen: set[str] = set()
    for g in generated:
        assert "error" not in g  # per-element failures never escape to gather
        for item in g["image_prompts"]:
            marker = item["image_prompt"].split()[1]
            seen.add(marker)
            err = fs.expected_error[marker]
            if err is None:
                # successes keep their image and are uploaded
                assert item["image_url"] == fs.expected_url[marker]
                assert "image_error" not in item
                assert item["element_id"] in uploaded_names
            else:
                assert item["image_url"] is None
                assert item["image_error"] == err
                assert item["element_id"] not in uploaded_names
                assert "image_id" not in item
    assert seen == set(fs.expected_error)
    assert len(run.upload.snapshots) == len(fs.expected_url)


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
