"""Unit tests for generation-failure marking and log sanitising in
`generate_images_from_prompts` (adset-creative-diversity, task 9.3, Req 11.1-11.6, 11.8)."""
import asyncio

import httpx
import pytest
from google import genai
from loguru import logger

from agents import nano_banana_agent
from tests._diversity_pipeline_fakes import (
    FakeGenaiClientFactory,
    FakeHttpResponse,
    FakeHttpxGet,
    make_genai_empty_response,
    make_genai_image_response,
    make_genai_text_response,
)

SECRET = "X-Amz-Signature=SECRETSIG&key=APIKEY123"
BASE_URL = f"https://bucket.example/base.png?{SECRET}"
PROD_URL = f"https://bucket.example/prod.png?{SECRET}"


def _prompt(n_items: int = 1, **extra) -> dict:
    return {
        "plan_id": "p1",
        "image_prompts": [
            {"element_id": f"e{i}", "image_prompt": f"prompt {i}"} for i in range(n_items)
        ],
        **extra,
    }


@pytest.fixture
def logs():
    lines: list[str] = []
    sink_id = logger.add(lambda m: lines.append(str(m)), format="{message}", level="DEBUG")
    yield lines
    logger.remove(sink_id)


@pytest.fixture
def patch_env(monkeypatch):
    uploads: list = []

    async def _upload(ad_id, image):
        uploads.append(image)
        return f"img-{len(uploads)}"

    monkeypatch.setattr(nano_banana_agent, "upload_image_to_library_tool", _upload)

    def _apply(genai_factory, httpx_get=None, upload=None):
        monkeypatch.setattr(genai, "Client", genai_factory)
        if httpx_get is not None:
            monkeypatch.setattr(httpx, "get", httpx_get)
        if upload is not None:
            monkeypatch.setattr(nano_banana_agent, "upload_image_to_library_tool", upload)
        return uploads

    return _apply


def _run(prompts, upload=True):
    return asyncio.run(
        nano_banana_agent.generate_images_from_prompts(prompts, 7, upload_image_to_library=upload)
    )


def test_safe_url_strips_query():
    assert nano_banana_agent._safe_url(BASE_URL) == "https://bucket.example/base.png"
    assert nano_banana_agent._safe_url(None) == ""


def test_client_creation_failure_marks_all_items(patch_env, logs):
    uploads = patch_env(FakeGenaiClientFactory(client_script=[RuntimeError(f"boom {SECRET}")]))
    out = _run([_prompt(2)])
    items = out["generated_images"][0]["image_prompts"]
    assert all(i["image_url"] is None and i["image_error"] == "RuntimeError" for i in items)
    assert uploads == []
    assert SECRET not in "".join(logs)


@pytest.mark.parametrize(
    "outcome,expected",
    [
        (asyncio.TimeoutError(), "TimeoutError"),
        (ValueError("bad"), "ValueError"),
        (make_genai_empty_response(), "NoImageInResponse"),
        (make_genai_text_response(), "NoImageInResponse"),
    ],
)
def test_item_failures_marked_and_not_uploaded(patch_env, outcome, expected):
    # second item fails, first and third succeed
    uploads = patch_env(FakeGenaiClientFactory(script=[make_genai_image_response(), outcome]))
    out = _run([_prompt(3)])
    items = out["generated_images"][0]["image_prompts"]
    assert items[0]["image_url"].startswith("data:image/")
    assert "image_error" not in items[0]
    assert items[1]["image_url"] is None and items[1]["image_error"] == expected
    assert items[2]["image_url"].startswith("data:image/")
    assert [u["image_name"] for u in uploads] == ["e0", "e2"]
    assert "image_id" not in items[1]


def test_download_failures_logged_without_query_and_skipped(patch_env, logs):
    fake_get = FakeHttpxGet(by_url={
        BASE_URL: [httpx.ConnectError(f"cannot reach {BASE_URL}")],
        PROD_URL: [FakeHttpResponse(status_code=403, content=b"")],
    })
    gen = FakeGenaiClientFactory()
    patch_env(gen, fake_get)
    out = _run([_prompt(1, base_image_url=BASE_URL, product_image_urls=[PROD_URL])], upload=False)
    item = out["generated_images"][0]["image_prompts"][0]
    assert item["image_url"].startswith("data:image/")
    assert gen.generate_count == 1
    # no image parts made it into the request: only the text part
    contents = gen.generate_calls[0]["kwargs"]["contents"]
    assert len(contents) == 1
    assert SECRET not in "".join(logs)
    assert "SECRETSIG" not in "".join(logs)
    assert "https://bucket.example/base.png" in "".join(logs)
    assert "ConnectError" in "".join(logs)


@pytest.mark.parametrize("upload_outcome", ["", RuntimeError(f"upload {SECRET}")])
def test_upload_failure_leaves_no_image_id(patch_env, logs, upload_outcome):
    async def _upload(ad_id, image):
        if isinstance(upload_outcome, Exception):
            raise upload_outcome
        return upload_outcome

    patch_env(FakeGenaiClientFactory(), upload=_upload)
    out = _run([_prompt(1)])
    item = out["generated_images"][0]["image_prompts"][0]
    assert item["image_url"].startswith("data:image/")
    assert "image_id" not in item
    assert "failed to upload" in "".join(logs)
    assert SECRET not in "".join(logs)


def test_gather_exception_records_class_name(patch_env, logs):
    patch_env(FakeGenaiClientFactory())
    original = nano_banana_agent.generate_images_from_prompts

    # Make _generate_single raise (escaping its own handlers) via a prompt whose
    # image_prompts access explodes
    class Exploding(dict):
        def get(self, key, default=None):
            if key == "image_prompts":
                raise KeyError(f"leak {SECRET}")
            return super().get(key, default)

    prompt = Exploding(plan_id="p9", variant_key="v1")
    out = asyncio.run(original([prompt], 7, upload_image_to_library=False))
    res = out["generated_images"][0]
    assert res == {"plan_id": "p9", "variant_key": "v1", "image_url": None, "error": "KeyError"}
    assert SECRET not in "".join(logs)
