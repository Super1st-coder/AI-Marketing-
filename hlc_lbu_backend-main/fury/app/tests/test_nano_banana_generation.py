"""Unit tests for `agents.nano_banana_agent.generate_images_from_prompts`
(adset-creative-diversity, Image_Generator: `image_prompt` in the upload and resilience).

No network and no LLM: `google.genai.Client`, `httpx.get` and the Upload_Tool are
replaced by the shared fakes (tests/_diversity_pipeline_fakes.py) through the
`run_generation` harness of tests/test_nano_banana_generation_properties.py, and any
real outbound call fails through `network_guard()`.

Run from fury/app:
    PYTHONPATH=. python -m pytest tests/test_nano_banana_generation.py
    PYTHONPATH=. python -m tests.test_nano_banana_generation
"""
from __future__ import annotations

import asyncio
import base64
from typing import Any

from tests._diversity_pipeline_fakes import (
    FakeGenaiClientFactory,
    FakeHttpResponse,
    FakeHttpxGet,
    make_genai_image_response,
    make_genai_text_response,
)
from tests.test_nano_banana_generation_properties import (
    GenerationRun,
    GenerationScenario,
    SnapshotUploadTool,
    capture_logs,
    run_generation,
)

AD_ID = 7
BASE_URL = "https://bucket.example/base.png?X-Amz-Signature=BASESIG"
PROD_URL_1 = "https://bucket.example/prod_1.jpg?X-Amz-Signature=PRODSIG1"
PROD_URL_2 = "https://bucket.example/prod_2.jpg?X-Amz-Signature=PRODSIG2"


def _prompt(items: list[dict[str, Any]], plan_id: str = "plan_1", **extra: Any) -> dict[str, Any]:
    return {"plan_id": plan_id, "image_prompts": items, **extra}


def _run(prompts: list[dict[str, Any]], **kwargs: Any) -> tuple[GenerationRun, list[str]]:
    scenario = GenerationScenario(prompts=prompts, gemini_script=[], diversity_flag=True, ad_id=AD_ID)
    return capture_logs(lambda: run_generation(scenario, **kwargs))


def _items(run: GenerationRun) -> dict[str, dict[str, Any]]:
    return {
        item["element_id"]: item
        for g in run.result["generated_images"]
        for item in g.get("image_prompts", [])
    }


def _warnings(lines: list[str], *needles: str) -> list[str]:
    return [l for l in lines if l.startswith("WARNING|") and any(n in l for n in needles)]


def _image_parts(contents: list[Any]) -> list[bytes]:
    return [p.inline_data.data for p in contents if getattr(p, "inline_data", None)]


# ---------------------------------------------------------------------------
# Requirement 9: image_prompt in the upload payload
# ---------------------------------------------------------------------------

def test_upload_payload_includes_image_prompt_when_present() -> None:
    """Req 9.1 / 12.9"""
    run, _ = _run([_prompt([{"element_id": "el_1", "image_prompt": "a red bike at dawn"}])])

    assert len(run.upload.snapshots) == 1
    payload = run.upload.snapshots[0]
    assert set(payload) == {"image_data", "image_name", "mime_type", "plan_id", "image_prompt"}
    assert payload["image_prompt"] == "a red bike at dawn"
    assert payload["image_name"] == "el_1"
    assert payload["plan_id"] == "plan_1"
    assert payload["image_data"].startswith("data:image/png;base64,")
    assert run.upload.calls[0].arguments["ad_id"] == AD_ID
    assert _items(run)["el_1"]["image_id"] == run.upload.uploaded_ids[0]


def test_upload_payload_image_prompt_empty_when_absent() -> None:
    """Req 9.2 / 12.9"""
    run, _ = _run([_prompt([{"element_id": "el_1"}])])

    assert len(run.upload.snapshots) == 1
    assert run.upload.snapshots[0]["image_prompt"] == ""
    assert "image_id" in _items(run)["el_1"]


def test_upload_payload_image_prompt_empty_when_not_a_string() -> None:
    """Req 9.2 / 12.9 — None, int, dict; product path so generation still succeeds."""
    items = [
        {"element_id": "el_none", "image_prompt": None},
        {"element_id": "el_int", "image_prompt": 42},
        {"element_id": "el_dict", "image_prompt": {"text": "x"}},
    ]
    run, _ = _run([_prompt(items, product_image_urls=[PROD_URL_1])])

    by_name = {s["image_name"]: s for s in run.upload.snapshots}
    assert set(by_name) == {"el_none", "el_int", "el_dict"}
    assert all(s["image_prompt"] == "" for s in by_name.values())
    # the original item value is not altered
    assert _items(run)["el_int"]["image_prompt"] == 42


# ---------------------------------------------------------------------------
# Requirement 11.1 / 11.2: failed downloads
# ---------------------------------------------------------------------------

def _assert_base_skipped(outcome: Any, needle: str) -> None:
    genai_factory = FakeGenaiClientFactory()
    run, lines = _run(
        [_prompt([{"element_id": "el_1", "image_prompt": "scene"}], base_image_url=BASE_URL)],
        genai_factory=genai_factory,
        httpx_get=FakeHttpxGet(by_url={BASE_URL: [outcome]}),
    )
    assert run.httpx_get.urls == [BASE_URL]
    # Gemini called anyway, without the base image
    assert genai_factory.generate_count == 1
    assert _image_parts(genai_factory.generate_calls[0]["kwargs"]["contents"]) == []
    warns = _warnings(lines, needle)
    assert len(warns) == 1
    assert "https://bucket.example/base.png" in warns[0]
    assert "BASESIG" not in warns[0]
    # job continues: image generated and uploaded
    item = _items(run)["el_1"]
    assert item["image_url"] and "image_error" not in item
    assert len(run.upload.snapshots) == 1


def test_base_image_download_exception_is_skipped() -> None:
    """Req 11.1 / 12.10"""
    _assert_base_skipped(ConnectionError(f"reset {BASE_URL}"), "failed to download")


def test_base_image_download_non_200_is_skipped() -> None:
    """Req 11.1 / 12.10"""
    _assert_base_skipped(FakeHttpResponse(status_code=403, content=b"denied"), "empty image bytes")


def test_base_image_download_empty_body_is_skipped() -> None:
    """Req 11.1 / 12.10"""
    _assert_base_skipped(FakeHttpResponse(content=b""), "empty image bytes")


def test_one_of_two_product_downloads_fails() -> None:
    """Req 11.2 / 12.10"""
    genai_factory = FakeGenaiClientFactory()
    run, lines = _run(
        [_prompt([{"element_id": "el_1", "image_prompt": "scene"}],
                 product_image_urls=[PROD_URL_1, PROD_URL_2])],
        genai_factory=genai_factory,
        httpx_get=FakeHttpxGet(by_url={
            PROD_URL_1: [ConnectionError("reset")],
            PROD_URL_2: [FakeHttpResponse(content=b"PROD2")],
        }),
    )
    assert run.httpx_get.urls == [PROD_URL_1, PROD_URL_2]
    assert genai_factory.generate_count == 1
    contents = genai_factory.generate_calls[0]["kwargs"]["contents"]
    assert _image_parts(contents) == [b"PROD2"]
    assert "scene" in contents[-1].text
    warns = _warnings(lines, "failed to download")
    assert len(warns) == 1 and "prod_1.jpg" in warns[0] and "PRODSIG1" not in warns[0]
    assert _items(run)["el_1"]["image_url"]
    assert len(run.upload.snapshots) == 1


# ---------------------------------------------------------------------------
# Requirement 11.3 / 11.4 / 11.5: Gemini failures
# ---------------------------------------------------------------------------

def _two_items() -> list[dict[str, Any]]:
    return [_prompt([
        {"element_id": "el_fail", "image_prompt": "first"},
        {"element_id": "el_ok", "image_prompt": "second"},
    ])]


def _assert_first_failed(run: GenerationRun, expected_error: str) -> None:
    items = _items(run)
    assert items["el_fail"]["image_url"] is None
    assert items["el_fail"]["image_error"] == expected_error
    assert "image_id" not in items["el_fail"]
    # the other element continues and is uploaded
    assert items["el_ok"]["image_url"] and "image_error" not in items["el_ok"]
    assert [s["image_name"] for s in run.upload.snapshots] == ["el_ok"]
    assert run.result["ok"] is True


def test_gemini_exception_marks_item_and_continues() -> None:
    """Req 11.3 / 12.17"""
    run, _ = _run(_two_items(), genai_factory=FakeGenaiClientFactory(
        script=[RuntimeError("boom"), make_genai_image_response()]
    ))
    _assert_first_failed(run, "RuntimeError")


def test_gemini_timeout_marks_item_and_continues() -> None:
    """Req 11.3 / 12.17 — asyncio.TimeoutError raised by the fake, no real wait."""
    run, _ = _run(_two_items(), genai_factory=FakeGenaiClientFactory(
        script=[asyncio.TimeoutError(), make_genai_image_response()]
    ))
    _assert_first_failed(run, "TimeoutError")


def test_gemini_response_without_inline_data() -> None:
    """Req 11.4 / 12.17"""
    run, _ = _run(_two_items(), genai_factory=FakeGenaiClientFactory(
        script=[make_genai_text_response(), make_genai_image_response()]
    ))
    _assert_first_failed(run, "NoImageInResponse")


# ---------------------------------------------------------------------------
# Requirement 11.6: upload failures
# ---------------------------------------------------------------------------

def _assert_upload_failure(outcome: Any) -> None:
    run, lines = _run(_two_items(), upload=SnapshotUploadTool(script=[outcome]))
    items = _items(run)
    # both images generated, both uploads attempted
    assert [s["image_name"] for s in run.upload.snapshots] == ["el_fail", "el_ok"]
    assert "image_id" not in items["el_fail"]
    assert items["el_ok"]["image_id"] == run.upload.uploaded_ids[0]
    errors = [l for l in lines if l.startswith("ERROR|") and "failed to upload" in l]
    assert len(errors) == 1


def test_upload_exception_leaves_item_without_image_id() -> None:
    """Req 11.6 / 12.17"""
    _assert_upload_failure(RuntimeError("sinergia down"))


def test_upload_empty_string_leaves_item_without_image_id() -> None:
    """Req 11.6 / 12.17"""
    _assert_upload_failure("")


# ---------------------------------------------------------------------------
# Requirement 9.7: no base64 nor prompt text in logs
# ---------------------------------------------------------------------------

def test_logs_never_contain_base64_nor_prompt_text() -> None:
    """Req 9.7 / 12.9"""
    image_bytes = b"\x89PNG-unique-binary-payload-0123456789"
    b64 = base64.b64encode(image_bytes).decode()
    prompt_text = "PROMPT_MARKER_7f3a scene"
    run, lines = _run(
        [_prompt([{"element_id": "el_1", "image_prompt": prompt_text}])],
        genai_factory=FakeGenaiClientFactory(script=[make_genai_image_response(data=image_bytes)]),
    )
    assert run.upload.snapshots[0]["image_data"].endswith(b64)
    upload_logs = [l for l in lines if "uploading image to library" in l]
    assert len(upload_logs) == 1
    assert f"image_data_len={len(run.upload.snapshots[0]['image_data'])}" in upload_logs[0]
    assert f"image_prompt_len={len(prompt_text)}" in upload_logs[0]
    for line in lines:
        assert b64 not in line
        assert "base64," not in line
        assert "PROMPT_MARKER_7f3a" not in line


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
