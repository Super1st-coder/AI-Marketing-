"""Unit tests for the Image_Editor `agents.nano_banana_agent.edit_image_variations`.

Covers: rate limit followed by success → 2 calls and the variation returned
(backoff via injected `sleep`), client-side timeout `max(10, setting)` and the
untouched signature of `generate_images_from_prompts`
(Req 7.2, 7.4, 7.6, 13.10).

`_call_nano_banana2_edit` and `_make_nano_banana2_client` are patched and every
test runs under `network_guard()`, so no real Gemini/network call can happen.

Runnable two ways:
    python -m tests.test_nano_banana_edit_variations
    pytest tests/test_nano_banana_edit_variations.py
"""
from __future__ import annotations

import asyncio
import base64
import inspect
from contextlib import contextmanager
from typing import Any, Iterator

from agents import nano_banana_agent
from core.config import settings
from tests._edit_pipeline_fakes import AttrPatcher, network_guard

BASE_BYTES = b"\x89PNG\r\n\x1a\nbase-image"
BASE_MIME = "image/png"
INSTRUCTION = "Expand the canvas to the right without modifying the existing content."
EDITED_BYTES = b"\x89PNG\r\n\x1a\nedited-image"

_SENTINEL_CLIENT = object()


class RateLimitError(Exception):
    """Error carrying the rate-limit markers recognised by _is_image_rate_limit_error."""

    def __init__(self) -> None:
        super().__init__("429 RESOURCE_EXHAUSTED: too many requests")


class FakeEditCall:
    """Scripted stand-in for `_call_nano_banana2_edit` that records every call."""

    def __init__(self, script: list[Any]) -> None:
        self.script = list(script)
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, client, image_bytes, mime_type, edit_instruction, timeout_s):
        self.calls.append({
            "client": client, "image_bytes": image_bytes, "mime_type": mime_type,
            "edit_instruction": edit_instruction, "timeout_s": timeout_s,
        })
        outcome = self.script.pop(0) if self.script else (EDITED_BYTES, "image/png")
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeClientFactory:
    """Stand-in for `_make_nano_banana2_client` recording the timeout it gets."""

    def __init__(self) -> None:
        self.timeouts: list[int] = []

    def __call__(self, timeout_s: int) -> Any:
        self.timeouts.append(timeout_s)
        return _SENTINEL_CLIENT


class RecordingSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


@contextmanager
def patched_editor(
    edit_call: FakeEditCall, *, timeout_setting: int | None = None,
) -> Iterator[FakeClientFactory]:
    factory = FakeClientFactory()
    patcher = AttrPatcher()
    try:
        with network_guard():
            patcher.set(nano_banana_agent, "_call_nano_banana2_edit", edit_call)
            patcher.set(nano_banana_agent, "_make_nano_banana2_client", factory)
            if timeout_setting is not None:
                patcher.set(settings, "IMAGE_GEN_TIMEOUT_SECONDS", timeout_setting)
            yield factory
    finally:
        patcher.undo()


def _run(n_variations: int = 1, sleep: Any = None) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {"task_id": "test-task"}
    if sleep is not None:
        kwargs["sleep"] = sleep
    return asyncio.run(nano_banana_agent.edit_image_variations(
        BASE_BYTES, BASE_MIME, INSTRUCTION, n_variations, **kwargs,
    ))


# ---------------------------------------------------------------------------
# Rate limit followed by success (Req 7.4, 13.10)
# ---------------------------------------------------------------------------

def test_rate_limit_then_success_makes_two_calls_and_returns_variation() -> None:
    edit_call = FakeEditCall([RateLimitError(), (EDITED_BYTES, "image/png")])
    sleep = RecordingSleep()
    with patched_editor(edit_call):
        result = _run(1, sleep=sleep)

    assert len(edit_call.calls) == 2
    assert sleep.delays == [1]  # first backoff step, simulated (no real wait)
    assert result == [{
        "index": 1,
        "image_b64": base64.b64encode(EDITED_BYTES).decode(),
        "mime_type": "image/png",
    }]
    # Both attempts send the original binary and the Edit_Instruction unchanged.
    for call in edit_call.calls:
        assert call["image_bytes"] == BASE_BYTES
        assert call["mime_type"] == BASE_MIME
        assert call["edit_instruction"] == INSTRUCTION
        assert call["client"] is _SENTINEL_CLIENT


def test_rate_limit_classifier_recognises_rate_limit_only() -> None:
    assert nano_banana_agent._is_image_rate_limit_error(RateLimitError())
    assert not nano_banana_agent._is_image_rate_limit_error(RuntimeError("boom"))


# ---------------------------------------------------------------------------
# Client-side timeout max(10, setting) (Req 7.6)
# ---------------------------------------------------------------------------

def test_timeout_is_floored_at_10_seconds() -> None:
    edit_call = FakeEditCall([])
    with patched_editor(edit_call, timeout_setting=3) as factory:
        _run(1, sleep=RecordingSleep())
    assert factory.timeouts == [10]
    assert [c["timeout_s"] for c in edit_call.calls] == [10]


def test_timeout_uses_setting_when_above_10_seconds() -> None:
    edit_call = FakeEditCall([])
    with patched_editor(edit_call, timeout_setting=45) as factory:
        _run(2, sleep=RecordingSleep())
    assert factory.timeouts == [45]
    assert [c["timeout_s"] for c in edit_call.calls] == [45, 45]


# ---------------------------------------------------------------------------
# generate_images_from_prompts untouched (Req 7.2)
# ---------------------------------------------------------------------------

def test_generate_images_from_prompts_signature_unchanged() -> None:
    fn = nano_banana_agent.generate_images_from_prompts
    assert inspect.iscoroutinefunction(fn)
    params = inspect.signature(fn).parameters
    assert list(params) == ["image_prompts", "ad_id", "upload_image_to_library"]
    assert params["image_prompts"].default is inspect.Parameter.empty
    assert params["ad_id"].default is inspect.Parameter.empty
    assert params["upload_image_to_library"].default is True
    assert all(p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params.values())


# ---------------------------------------------------------------------------
# Property 10 (Req 7.1, 7.3, 7.4, 7.5, 7.7, 13.10)
# ---------------------------------------------------------------------------

from hypothesis import given, settings as hyp_settings, strategies as st  # noqa: E402

_BACKOFF = [1, 2, 4]


def _current_variation_index() -> int:
    """Index of the `_one(index)` coroutine driving the current asyncio task.

    Calls from concurrent variations interleave nondeterministically, so the
    per-variation script is resolved from the running task instead of call order.
    """
    frame = asyncio.current_task().get_coro().cr_frame
    return frame.f_locals["index"]


class ScriptedPerVariationEdit:
    """Fake `_call_nano_banana2_edit` with a script per variation and an in-flight gauge."""

    def __init__(self, scripts: dict[int, list[Any]]) -> None:
        self.scripts = {i: list(s) for i, s in scripts.items()}
        self.calls: dict[int, int] = {i: 0 for i in scripts}
        self.in_flight = 0
        self.max_in_flight = 0

    async def __call__(self, client, image_bytes, mime_type, edit_instruction, timeout_s):
        index = _current_variation_index()
        assert image_bytes == BASE_BYTES and edit_instruction == INSTRUCTION
        self.calls[index] += 1
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            for _ in range(3):  # yield so other variations can try to enter
                await asyncio.sleep(0)
            outcome = self.scripts[index].pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome
        finally:
            self.in_flight -= 1


class PerVariationSleep:
    def __init__(self) -> None:
        self.delays: dict[int, list[float]] = {}

    async def __call__(self, delay: float) -> None:
        self.delays.setdefault(_current_variation_index(), []).append(delay)


_MIMES = st.sampled_from(["image/png", "image/jpeg", "image/webp"])
_OUTCOME = st.one_of(
    st.tuples(st.just("ok"), _MIMES),
    st.tuples(st.just("rl"), st.integers(min_value=1, max_value=4), _MIMES),
    st.tuples(st.just("err")),
    st.tuples(st.just("timeout")),
    st.tuples(st.just("noimg")),
)


def _script_for(outcome: tuple, index: int) -> list[Any]:
    kind = outcome[0]
    ok = (EDITED_BYTES + bytes([index]), outcome[-1]) if kind in ("ok", "rl") else None
    if kind == "ok":
        return [ok]
    if kind == "rl":
        k = outcome[1]
        return [RateLimitError() for _ in range(k)] + [ok]
    if kind == "err":
        return [RuntimeError("boom")]
    if kind == "timeout":
        return [asyncio.TimeoutError()]
    return [None]  # response without image


# Feature: ad-variant-image-edit-pipeline, Property 10: Contabilidad de solicitudes del Image_Editor
@hyp_settings(max_examples=100, deadline=None)
@given(
    outcomes=st.lists(_OUTCOME, min_size=1, max_size=10),
    concurrency=st.integers(min_value=1, max_value=4),
)
def test_property_10_image_editor_request_accounting(outcomes: list[tuple], concurrency: int) -> None:
    """**Validates: Requirements 7.1, 7.3, 7.4, 7.5, 7.7, 13.10**"""
    n = len(outcomes)
    scripts = {i: _script_for(o, i) for i, o in enumerate(outcomes, start=1)}
    edit_call = ScriptedPerVariationEdit(scripts)
    sleep = PerVariationSleep()

    patcher = AttrPatcher()
    try:
        patcher.set(settings, "IMAGE_GEN_MAX_CONCURRENCY", concurrency)
        # Fresh semaphore per example, built from the patched limit.
        nano_banana_agent._img_semaphores.clear()
        with patched_editor(edit_call):
            result = asyncio.run(nano_banana_agent.edit_image_variations(  # (e) never raises
                BASE_BYTES, BASE_MIME, INSTRUCTION, n, task_id="prop-10", sleep=sleep,
            ))
    finally:
        patcher.undo()
        nano_banana_agent._img_semaphores.clear()

    # (a) exactly the variations whose script ends in success, sorted by index
    expected_ok = [
        i for i, o in enumerate(outcomes, start=1)
        if o[0] == "ok" or (o[0] == "rl" and o[1] <= 3)
    ]
    assert [v["index"] for v in result] == expected_ok
    for v in result:
        o = outcomes[v["index"] - 1]
        assert set(v) == {"index", "image_b64", "mime_type"}
        assert v["image_b64"] == base64.b64encode(EDITED_BYTES + bytes([v["index"]])).decode()
        assert v["mime_type"] == o[-1] and v["mime_type"].startswith("image/")

    for i, o in enumerate(outcomes, start=1):
        k = o[1] if o[0] == "rl" else 0
        # (b) 1 + min(k, 3) calls with k rate limits; 1 call for non rate-limit outcomes
        assert edit_call.calls[i] == 1 + min(k, 3)
        # (c) backoff sequence [1, 2, 4][:min(k, 3)]
        assert sleep.delays.get(i, []) == _BACKOFF[:min(k, 3)]

    # (d) never more than c calls in flight
    assert 1 <= edit_call.max_in_flight <= concurrency
    assert edit_call.in_flight == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all nano banana edit variations tests passed")
