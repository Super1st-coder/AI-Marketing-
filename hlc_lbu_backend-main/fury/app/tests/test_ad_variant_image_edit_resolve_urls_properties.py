"""Property 20 of the ad-variant image-edit pipeline: URL_Resolution with
bounded retries (`resolve_urls` step).

Runs `_run_edit_ad_variant_image_pipeline` fully in memory, resuming from a
pre-loaded `upload` checkpoint (no `resolve_urls` checkpoint), with a scripted
`get_ad_variant_image` per library id and a simulated Edit_Sleep.

Run: PYTHONPATH=. python -m pytest tests/test_ad_variant_image_edit_resolve_urls_properties.py
  or PYTHONPATH=. python -m tests.test_ad_variant_image_edit_resolve_urls_properties
"""
from __future__ import annotations

import asyncio
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from core.exceptions import VariationUrlResolutionError
from services import job_runner_service as jrs
from tests._edit_pipeline_fakes import (
    FakeGetAdVariantImage,
    FakeRedis,
    FakeSleep,
    FakeTask,
    cp_key,
    make_variations,
    patched_pipeline,
    signed_url,
)

_TASK_ID = "resolve-urls-task-id"
_AD_ID = 3
_ID_BASE_IMAGE = "base-img-123"
_LIBRARY_INDEX_DELAY_S = 15
_RESOLVE_URL_RETRY_DELAY_S = 5
_MAX_QUERIES = 4
_REQUEST = dict(
    brand_id=1,
    campaign_id=2,
    ad_id=_AD_ID,
    channel_id=4,
    variant_id=5,
    image_name="banner.png",
    id_base_image=_ID_BASE_IMAGE,
    custom_prompt="Make the background a sunny beach",
    expand_zoom_option=None,
)


# ---------------------------------------------------------------------------
# Recording fakes (shared timeline of sleeps and URL_Resolution calls)
# ---------------------------------------------------------------------------


class _TimelineSleep(FakeSleep):
    def __init__(self, timeline: list[tuple[str, Any]]) -> None:
        super().__init__()
        self.timeline = timeline

    async def __call__(self, seconds: float, *args: Any, **kwargs: Any) -> None:
        self.timeline.append(("sleep", seconds))
        return await super().__call__(seconds, *args, **kwargs)


class _TimelineGet(FakeGetAdVariantImage):
    def __init__(self, timeline: list[tuple[str, Any]], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.timeline = timeline

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        bound = self._bind(args, kwargs)
        self.timeline.append(("get", str(bound.get("id_base_image"))))
        return await super().__call__(*args, **kwargs)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_ids = st.lists(
    st.integers(min_value=1, max_value=10_000).map(lambda n: f"lib-{n}"),
    min_size=1, max_size=10, unique=True,
)
_prompts = st.text(min_size=1, max_size=40).filter(lambda s: s.strip())
_messages = st.one_of(
    st.text(max_size=40),
    st.integers(1, 99).map(lambda n: f"sinergia 500 at {signed_url('library/err.png', n)}"),
)
_valid_urls = st.one_of(
    st.integers(1, 999).map(lambda n: signed_url(f"library/ok_{n}.png", n)),
    st.integers(1, 999).map(lambda n: f"https://cdn.example.com/img_{n}.png"),
    st.text(min_size=1, max_size=40).filter(lambda s: s.strip()),
)


@st.composite
def _outcome(draw: Any, image_id: str) -> tuple[str, Any]:
    """`(kind, value)`; kind == "valid" iff the pipeline must accept it."""
    kind = draw(st.sampled_from(
        ["exception", "not_dict", "other_id", "missing_url", "blank_url", "valid"]
    ))
    if kind == "exception":
        exc_type = draw(st.sampled_from([RuntimeError, ValueError, ConnectionError, KeyError]))
        return kind, exc_type(draw(_messages))
    if kind == "not_dict":
        return kind, draw(st.one_of(
            st.none(), st.text(max_size=20), st.integers(),
            st.lists(st.integers(), max_size=3),
        ))
    if kind == "other_id":
        other = draw(st.text(max_size=12).filter(lambda s: s != image_id))
        return kind, {"id": other, "url": draw(_valid_urls), "prompt": ""}
    if kind == "missing_url":
        return kind, {"id": image_id, "prompt": ""}
    if kind == "blank_url":
        blank = draw(st.one_of(st.sampled_from(["", " ", "  \t", "\n"]), st.none(), st.integers()))
        return kind, {"id": image_id, "url": blank, "prompt": ""}
    return kind, {"id": image_id, "url": draw(_valid_urls), "prompt": draw(st.text(max_size=10))}


@st.composite
def _scenario(draw: Any) -> tuple[list[dict[str, str]], dict[str, list[tuple[str, Any]]]]:
    ids = draw(_ids)
    uploaded = [{"id": i, "prompt": draw(_prompts)} for i in ids]
    scripts = {
        i: draw(st.lists(_outcome(i), min_size=1, max_size=6)) for i in ids
    }
    return uploaded, scripts


def _effective_script(image_id: str, script: list[tuple[str, Any]]) -> list[tuple[str, Any]]:
    """Script plus an explicit valid fallback, equivalent to the fake's default
    once the script is exhausted (so the accepted url is known in advance)."""
    fallback = {"id": image_id, "url": signed_url(f"library/{image_id}.png", 0), "prompt": ""}
    return [*script, ("valid", fallback)]


def _first_valid(script: list[tuple[str, Any]]) -> int:
    """1-based position of the first accepted outcome; an exhausted script falls
    back to a valid response, i.e. position len + 1."""
    for pos, (kind, _) in enumerate(script, start=1):
        if kind == "valid":
            return pos
    return len(script) + 1


# ---------------------------------------------------------------------------
# Property 20
# ---------------------------------------------------------------------------


# Feature: ad-variant-image-edit-pipeline, Property 20: Resolución de URLs con reintentos acotados
@settings(max_examples=100, deadline=None)
@given(_scenario())
def test_resolve_urls_bounded_retries(scenario):
    """**Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8,
    14.10, 14.11, 9.11, 13.24, 13.25, 13.26, 13.28**"""
    uploaded, scripts = scenario
    ids = [u["id"] for u in uploaded]
    n = len(uploaded)

    redis = FakeRedis()
    indices = list(range(1, n + 1))
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "fetch_base_image", {
        "id": _ID_BASE_IMAGE,
        "url": "https://fake-bucket.s3.us-east-2.amazonaws.com/base.png",
        "prompt": "p",
    })
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "image_editing", make_variations(indices))
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "prompt_analysis", [
        {**v, "prompt": f"checkpoint prompt {v['index']}", "prompt_source": "agent"}
        for v in make_variations(indices)
    ])
    redis.seed_checkpoint(_TASK_ID, _AD_ID, "upload", uploaded)

    timeline: list[tuple[str, Any]] = []
    get_image = _TimelineGet(
        timeline,
        resolutions={i: [value for _, value in _effective_script(i, scripts[i])] for i in ids},
        base_image_id=_ID_BASE_IMAGE,
    )
    sleep = _TimelineSleep(timeline)

    raised: BaseException | None = None
    result: dict[str, Any] | None = None
    with patched_pipeline(
        redis=redis, get_ad_variant_image=get_image, sleep=sleep, id_base_image=_ID_BASE_IMAGE,
    ) as h:
        try:
            result = asyncio.run(jrs._run_edit_ad_variant_image_pipeline(
                FakeTask(_TASK_ID, retries=1), _TASK_ID, n_variations=n, **_REQUEST,
            ))
        except VariationUrlResolutionError as exc:
            raised = exc

    # Expected queries per id: min(p, 4); resolved iff p <= 4.
    expected_queries = {i: min(_first_valid(scripts[i]), _MAX_QUERIES) for i in ids}
    resolved_ids = [i for i in ids if _first_valid(scripts[i]) <= _MAX_QUERIES]
    omitted_ids = [i for i in ids if i not in resolved_ids]

    # No re-upload, no base fetch.
    assert h.upload.call_count == 0
    assert get_image.base_call_count == 0

    # Edit_Sleep(15) once, first, before the first URL_Resolution.
    assert timeline[0] == ("sleep", _LIBRARY_INDEX_DELAY_S)
    total_retries = sum(q - 1 for q in expected_queries.values())
    assert sleep.calls == [_LIBRARY_INDEX_DELAY_S] + [_RESOLVE_URL_RETRY_DELAY_S] * total_retries

    # Sequential, in checkpoint order; sleeps only between queries of the same id.
    expected_timeline: list[tuple[str, Any]] = [("sleep", _LIBRARY_INDEX_DELAY_S)]
    for i in ids:
        for q in range(expected_queries[i]):
            if q > 0:
                expected_timeline.append(("sleep", _RESOLVE_URL_RETRY_DELAY_S))
            expected_timeline.append(("get", i))
    assert timeline == expected_timeline

    # Every URL_Resolution carries the request's arguments; never a 5th query.
    for i in ids:
        calls = get_image.resolution_calls_for(i)
        assert len(calls) == expected_queries[i] <= _MAX_QUERIES
        for c in calls:
            assert c["id_base_image"] == i
            for name in ("brand_id", "campaign_id", "ad_id", "channel_id", "variant_id", "image_name"):
                assert c[name] == _REQUEST[name]

    # Expected Registered_Variants: url of the accepted response, unmodified.
    expected_variations = []
    for i, item in zip(ids, uploaded):
        if i not in resolved_ids:
            continue
        url = _effective_script(i, scripts[i])[expected_queries[i] - 1][1]["url"]
        expected_variations.append({"id": i, "url": url, "prompt": item["prompt"]})

    # Omitted ids are logged with task id, id and number of queries.
    warnings = h.logs.at_level("WARNING")
    for i in omitted_ids:
        assert any(
            f"[{_TASK_ID}]" in line and f"id={i} " in line and "skipped" in line
            and f"{_MAX_QUERIES} queries" in line
            for line in warnings
        ), f"no skip log for {i}"

    resolve_key = cp_key(_TASK_ID, _AD_ID, "resolve_urls")
    if not resolved_ids:
        assert raised is not None and result is None
        assert raised.retryable is True
        assert raised.details["step"] == "resolve_urls"
        assert redis.writes_for(resolve_key) == []
        assert redis.checkpoint(_TASK_ID, _AD_ID, "resolve_urls") is None
        assert redis.checkpoint(_TASK_ID, _AD_ID, "upload") == uploaded
        return

    assert raised is None and result is not None
    assert result["status"] == "DONE"
    assert result["variations"] == expected_variations
    assert len(result["variations"]) + len(omitted_ids) == n
    assert redis.checkpoint(_TASK_ID, _AD_ID, "resolve_urls") == jrs._strip_signed_urls(
        expected_variations
    )


# ---------------------------------------------------------------------------
# __main__ runner
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
