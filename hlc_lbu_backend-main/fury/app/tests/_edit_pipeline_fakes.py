"""Shared fakes for the ad-variant image-edit pipeline tests (not a test module).

Used by tests/test_ad_variant_image_edit_*.py to run
`services.job_runner_service._run_edit_ad_variant_image_pipeline`, its Celery
task and the `/variants/image/edit` endpoints fully in memory: no Redis, no
Sinergia, no Gemini, no LLM and no network (Req 13.1, 13.2).

Contents:
    FakeRedis                  in-memory Redis with a log of every set(key, value, ex)
    FakeTask / FakeRetry       Celery-task stand-in (update_state, retry, request.*)
    ScriptedAsyncFake          base for scripted async fakes with call recording
    FakeGetAdVariantImage      get_ad_variant_image (Base_Image call vs URL_Resolution
                               calls, told apart by `id_base_image`; per-id scripts)
    FakeUploadImageToLibrary   upload_image_to_library(ad_id, image_data) -> str
    FakeSleep                  job_runner_service._edit_sleep (records seconds, no wait)
    FakeDownloadBaseImage      _download_base_image
    FakeEditImageVariations    edit_image_variations
    FakeRunAgent               helpers.agent.run_agent (as `_run_agent`)
    FakePrompterFactory        make_ad_variant_image_prompter_agent
    LogCapture                 loguru sink that captures log lines
    network_guard()            blocks real httpx / socket traffic
    patched_pipeline(...)      monkeypatches everything above and restores it

Patching is tolerant of attributes that do not exist yet (other tasks of the
spec add them): a missing attribute is created during the context and deleted
on exit; a missing module is skipped and reported in `PipelineHarness.skipped`.

Scripts: every scripted fake consumes one outcome per call, in order. An
outcome can be
    - an exception instance or class  -> raised
    - a callable                      -> called with the call's (*args, **kwargs);
                                         awaited if it returns an awaitable
    - DEFAULT                         -> the fake's default behaviour
    - any other value                 -> returned (deep-copied)
When the script is exhausted the default behaviour is used.
"""
from __future__ import annotations

import base64
import copy
import importlib
import inspect
import itertools
import json
import socket
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Iterable, Iterator

import httpx
from loguru import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNMOCKED_NETWORK_MSG = "unmocked network call"
CHECKPOINT_TTL = 7200  # mirrors services.job_runner_service._CHECKPOINT_TTL
DEFAULT_TASK_ID = "test-task-id"
DEFAULT_INTERNAL_API_KEY = "test-internal-api-key-0123456789"
DEFAULT_SINERGIA_API_KEY = "test-sinergia-service-key-9876543210"
DEFAULT_BASE_PROMPT = "A bright product shot on a white table"
# Minimal PNG signature + payload: non-empty, deterministic, never decoded.
DEFAULT_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-base-image-bytes"
DEFAULT = object()  # script sentinel → use the fake's default behaviour

_JOB_RUNNER = "services.job_runner_service"
_NANO_BANANA = "agents.nano_banana_agent"
_CAMPAIGN_TOOLS = "agents.tools.campaign_tools"
_MOCK_SINERGIA = "agents.tools.mock_sinergia"
_PROMPTER_AGENT = "agents.ad_variant_image_prompter_agent"


def cp_key(task_id: str, ad_id: Any, step: str) -> str:
    """Checkpoint key, same format as services.job_runner_service._cp_key."""
    return f"fury:cp:{task_id}:{ad_id}:{step}"


def signed_url(path: str = "base.png", n: int | str = 1) -> str:
    """S3-style presigned URL (X-Amz-*) to exercise _strip_signed_urls."""
    return (
        f"https://fake-bucket.s3.us-east-2.amazonaws.com/{path}"
        f"?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=FAKE{n}"
        f"&X-Amz-Expires=3600&X-Amz-Signature=fakesig{n}"
    )


def make_variations(
    indices: Iterable[int], mime_type: str = "image/png"
) -> list[dict[str, Any]]:
    """Edited_Variation list for the given 1-based indices, sorted by index."""
    return [
        {
            "index": i,
            "image_b64": base64.b64encode(f"edited-variation-{i}".encode()).decode(),
            "mime_type": mime_type,
        }
        for i in sorted(indices)
    ]


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SetCall:
    """One recorded `set(key, value, ex)`; `value` is the raw (JSON) string."""

    key: str
    value: str
    ex: int | None

    @property
    def decoded(self) -> Any:
        return json.loads(self.value)


def _default_redis_error() -> BaseException:
    try:
        from redis.exceptions import ConnectionError as RedisConnectionError

        return RedisConnectionError("fake redis unavailable")
    except ImportError:  # pragma: no cover - redis is a runtime dependency
        return ConnectionError("fake redis unavailable")


class FakeRedis:
    """In-memory replacement for the client returned by `_redis()`.

    Patched in as `services.job_runner_service._redis`, so the real `_store` /
    `_load` (and therefore `_edit_cp_store` / `_edit_cp_load`) run unchanged on
    top of it. Set `fail_on={"get"}` / `{"set"}` to simulate Redis outages (D8).
    """

    def __init__(
        self,
        initial: dict[str, Any] | None = None,
        *,
        fail_on: Iterable[str] = (),
        error: BaseException | None = None,
    ) -> None:
        self.data: dict[str, str] = {}
        self.sets: list[SetCall] = []
        self.gets: list[str] = []
        self.fail_on: set[str] = set(fail_on)
        self.error = error
        for key, value in (initial or {}).items():
            self.seed(key, value)

    # -- redis-py surface used by job_runner_service ---------------------
    def set(self, key: str, value: Any, ex: int | None = None, **_: Any) -> bool:
        self._maybe_fail("set")
        value = value if isinstance(value, str) else str(value)
        self.sets.append(SetCall(key=key, value=value, ex=ex))
        self.data[key] = value
        return True

    def get(self, key: str) -> str | None:
        self._maybe_fail("get")
        self.gets.append(key)
        return self.data.get(key)

    def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            removed += int(self.data.pop(key, None) is not None)
        return removed

    def exists(self, *keys: str) -> int:
        return sum(1 for k in keys if k in self.data)

    # -- test helpers ------------------------------------------------------
    def seed(self, key: str, value: Any) -> None:
        """Pre-load a JSON value without recording it as a pipeline write."""
        self.data[key] = json.dumps(value)

    def seed_checkpoint(self, task_id: str, ad_id: Any, step: str, value: Any) -> None:
        self.seed(cp_key(task_id, ad_id, step), value)

    def load(self, key: str) -> Any:
        """Same semantics as `_load`: JSON-decoded value or None."""
        raw = self.data.get(key)
        return json.loads(raw) if raw else None

    def checkpoint(self, task_id: str, ad_id: Any, step: str) -> Any:
        return self.load(cp_key(task_id, ad_id, step))

    def writes_for(self, key: str) -> list[SetCall]:
        return [s for s in self.sets if s.key == key]

    @property
    def written_keys(self) -> list[str]:
        return [s.key for s in self.sets]

    def _maybe_fail(self, op: str) -> None:
        if op in self.fail_on:
            raise self.error if self.error is not None else _default_redis_error()


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


class FakeRetry(Exception):
    """Raised by `FakeTask.retry`, like celery.exceptions.Retry."""

    def __init__(self, exc: BaseException | None = None, countdown: Any = None) -> None:
        super().__init__(f"retry in {countdown}s: {type(exc).__name__ if exc else None}")
        self.exc = exc
        self.countdown = countdown


class FakeTask:
    """Bound-task stand-in: `request.id`, `request.retries`, `max_retries`,
    recorded `update_state` and simulated `retry`.

    `retry()` records the call and raises `FakeRetry`. If retries are already
    exhausted it re-raises `exc` (Celery 5.6 behaviour, design D7).
    """

    def __init__(
        self, task_id: str = DEFAULT_TASK_ID, retries: int = 0, max_retries: int = 3
    ) -> None:
        self.request = SimpleNamespace(id=task_id, retries=retries)
        self.max_retries = max_retries
        self.updates: list[dict[str, Any]] = []
        self.retry_calls: list[dict[str, Any]] = []

    def update_state(self, state: str | None = None, meta: dict | None = None, **_: Any) -> None:
        self.updates.append({"state": state, "meta": copy.deepcopy(meta)})

    def retry(self, exc: BaseException | None = None, countdown: Any = None, **kwargs: Any):
        self.retry_calls.append({"exc": exc, "countdown": countdown, **kwargs})
        if self.request.retries >= self.max_retries and exc is not None:
            raise exc
        raise FakeRetry(exc=exc, countdown=countdown)

    @property
    def steps(self) -> list[Any]:
        """`meta["step"]` of each update_state, in order."""
        return [(u["meta"] or {}).get("step") for u in self.updates]


# ---------------------------------------------------------------------------
# Scripted async fakes
# ---------------------------------------------------------------------------


@dataclass
class Call:
    """One recorded invocation. `arguments` maps parameter names → values."""

    args: tuple
    kwargs: dict[str, Any]
    arguments: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, name: str) -> Any:
        return self.arguments[name]


class ScriptedAsyncFake:
    """Async callable that records calls and replays a script of outcomes."""

    PARAMS: tuple[str, ...] = ()

    def __init__(self, script: Iterable[Any] | None = None) -> None:
        self.script: list[Any] = list(script or [])
        self.calls: list[Call] = []
        self.results: list[Any] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def push(self, *outcomes: Any) -> "ScriptedAsyncFake":
        self.script.extend(outcomes)
        return self

    def default(self, *args: Any, **kwargs: Any) -> Any:  # overridden
        return None

    def _bind(self, args: tuple, kwargs: dict[str, Any]) -> dict[str, Any]:
        bound = dict(zip(self.PARAMS, args))
        for extra_i, value in enumerate(args[len(self.PARAMS):]):
            bound[f"_arg{len(self.PARAMS) + extra_i}"] = value
        bound.update(kwargs)
        return bound

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(Call(args=args, kwargs=dict(kwargs), arguments=self._bind(args, kwargs)))
        outcome = self.script.pop(0) if self.script else DEFAULT
        result = await self._resolve(outcome, args, kwargs)
        self.results.append(result)
        return result

    async def _resolve(self, outcome: Any, args: tuple, kwargs: dict[str, Any]) -> Any:
        if outcome is DEFAULT:
            result = self.default(*args, **kwargs)
        elif isinstance(outcome, BaseException):
            raise outcome
        elif isinstance(outcome, type) and issubclass(outcome, BaseException):
            raise outcome()
        elif callable(outcome):
            result = outcome(*args, **kwargs)
        else:
            return copy.deepcopy(outcome)
        if inspect.isawaitable(result):
            result = await result
        return result


class FakeGetAdVariantImage(ScriptedAsyncFake):
    """Fake `get_ad_variant_image`, used both for the Base_Image fetch and for
    each URL_Resolution of the `resolve_urls` step.

    A call is the Base_Image call when its `id_base_image` equals the request's
    `id_base_image` (`base_image_id`). If `base_image_id` is not given (and not
    set by `patched_pipeline(id_base_image=...)`), the first call whose id is
    not a known resolution id (a key of `resolutions` or an id returned by the
    linked `FakeUploadImageToLibrary`) fixes it.

    Scripts:
        script        outcomes for the Base_Image calls, in order
        resolutions   `{image_id: [outcomes...]}` for the URL_Resolution of that id

    Defaults:
        Base_Image      `{"id": id_base_image, "url": <fresh signed URL>, "prompt": prompt}`
        URL_Resolution  `{"id": image_id, "url": <fresh signed URL>, "prompt": ""}`

    `calls`/`results`/`call_count` cover every call; `base_calls`/`base_results`
    and `resolution_calls`/`resolution_results` split them. `returned_urls`
    keeps the URL handed out on each Base_Image call (Req 13.23).
    """

    PARAMS = (
        "brand_id", "campaign_id", "ad_id", "channel_id", "variant_id",
        "image_name", "id_base_image",
    )

    def __init__(
        self,
        script: Iterable[Any] | None = None,
        *,
        resolutions: dict[Any, Iterable[Any]] | None = None,
        base_image_id: Any = None,
        prompt: str = DEFAULT_BASE_PROMPT,
    ) -> None:
        super().__init__(script)
        self.resolutions: dict[str, list[Any]] = {
            str(k): list(v) for k, v in (resolutions or {}).items()
        }
        self.base_image_id: str | None = (
            str(base_image_id) if base_image_id is not None else None
        )
        self.prompt = prompt
        self.base_calls: list[Call] = []
        self.base_results: list[Any] = []
        self.resolution_calls: list[Call] = []
        self.resolution_results: list[Any] = []
        self._upload: "FakeUploadImageToLibrary | None" = None
        self._counter = itertools.count(1)

    # -- configuration -----------------------------------------------------
    def link_upload(self, upload: "FakeUploadImageToLibrary") -> "FakeGetAdVariantImage":
        """Treat ids returned by `upload` as URL_Resolution ids."""
        self._upload = upload
        return self

    def push_resolution(self, image_id: Any, *outcomes: Any) -> "FakeGetAdVariantImage":
        self.resolutions.setdefault(str(image_id), []).extend(outcomes)
        return self

    # -- classification ----------------------------------------------------
    def _known_resolution_ids(self) -> set[str]:
        ids = set(self.resolutions)
        if self._upload is not None:
            ids.update(r for r in self._upload.results if isinstance(r, str) and r)
        return ids

    def is_base_call(self, image_id: Any) -> bool:
        image_id = str(image_id)
        if self.base_image_id is None:
            if image_id in self._known_resolution_ids():
                return False
            self.base_image_id = image_id
        return image_id == self.base_image_id

    # -- call ----------------------------------------------------------------
    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        bound = self._bind(args, kwargs)
        call = Call(args=args, kwargs=dict(kwargs), arguments=bound)
        self.calls.append(call)
        image_id = str(bound.get("id_base_image", ""))
        is_base = self.is_base_call(image_id)
        if is_base:
            self.base_calls.append(call)
            outcome = self.script.pop(0) if self.script else DEFAULT
        else:
            self.resolution_calls.append(call)
            pending = self.resolutions.get(image_id)
            outcome = pending.pop(0) if pending else DEFAULT
        result = await self._resolve(outcome, args, kwargs)
        self.results.append(result)
        (self.base_results if is_base else self.resolution_results).append(result)
        return result

    def default(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        bound = self._bind(args, kwargs)
        image_id = str(bound.get("id_base_image", ""))
        n = next(self._counter)
        if image_id == self.base_image_id:
            return {
                "id": image_id,
                "url": signed_url(f"base_{bound.get('variant_id', 'x')}.png", n),
                "prompt": self.prompt,
            }
        return {
            "id": image_id,
            "url": signed_url(f"library/{image_id}.png", n),
            "prompt": "",
        }

    # -- views -----------------------------------------------------------------
    @property
    def base_call_count(self) -> int:
        return len(self.base_calls)

    @property
    def resolution_call_count(self) -> int:
        return len(self.resolution_calls)

    @property
    def returned_urls(self) -> list[str]:
        """URL handed out on each Base_Image call."""
        return [r.get("url") for r in self.base_results if isinstance(r, dict)]

    @property
    def resolution_urls(self) -> list[str]:
        return [r.get("url") for r in self.resolution_results if isinstance(r, dict)]

    @property
    def resolved_ids(self) -> list[str]:
        """`id_base_image` of each URL_Resolution call, in order."""
        return [str(c.arguments.get("id_base_image")) for c in self.resolution_calls]

    def resolution_calls_for(self, image_id: Any) -> list[Call]:
        return [
            c for c in self.resolution_calls
            if str(c.arguments.get("id_base_image")) == str(image_id)
        ]


class FakeUploadImageToLibrary(ScriptedAsyncFake):
    """Fake `upload_image_to_library(ad_id, image_data) -> str`.

    Default: a unique non-empty `image_id` per call (`fake_img_<ad_id>_<n>`).
    Script outcomes may be `""`, non-`str` values (returned as-is) or exceptions.
    """

    PARAMS = ("ad_id", "image_data")

    def __init__(self, script: Iterable[Any] | None = None) -> None:
        super().__init__(script)
        self._counter = itertools.count(1)

    def default(self, *args: Any, **kwargs: Any) -> str:
        bound = self._bind(args, kwargs)
        return f"fake_img_{bound.get('ad_id', 'x')}_{next(self._counter)}"

    @property
    def payloads(self) -> list[dict[str, Any]]:
        return [c.arguments.get("image_data") for c in self.calls]

    @property
    def uploaded_ids(self) -> list[str]:
        """Non-empty `str` ids returned (the successful uploads)."""
        return [r for r in self.results if isinstance(r, str) and r.strip()]


class FakeSleep:
    """Async stand-in for `asyncio.sleep` (patched as `job_runner_service._edit_sleep`).

    Records the seconds requested and returns immediately.
    """

    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float, *args: Any, **kwargs: Any) -> None:
        self.calls.append(seconds)
        return None

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def total(self) -> float:
        return float(sum(self.calls))


class FakeDownloadBaseImage(ScriptedAsyncFake):
    """Fake `_download_base_image(url, task_id)`. Default: `(DEFAULT_IMAGE_BYTES, mime)`."""

    PARAMS = ("url", "task_id")

    def __init__(
        self,
        script: Iterable[Any] | None = None,
        *,
        body: bytes = DEFAULT_IMAGE_BYTES,
        mime_type: str = "image/png",
    ) -> None:
        super().__init__(script)
        self.body = body
        self.mime_type = mime_type

    def default(self, *args: Any, **kwargs: Any) -> tuple[bytes, str]:
        return self.body, self.mime_type

    @property
    def urls(self) -> list[str]:
        return [c.arguments.get("url") for c in self.calls]


class FakeEditImageVariations(ScriptedAsyncFake):
    """Fake `edit_image_variations`. Default: all `n_variations` succeed."""

    PARAMS = ("base_image_bytes", "base_mime_type", "edit_instruction", "n_variations")

    def __init__(
        self, script: Iterable[Any] | None = None, *, mime_type: str = "image/png"
    ) -> None:
        super().__init__(script)
        self.mime_type = mime_type

    def default(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        n = int(self._bind(args, kwargs).get("n_variations", 1))
        return make_variations(range(1, n + 1), self.mime_type)

    @staticmethod
    def succeed_only(indices: Iterable[int], mime_type: str = "image/png") -> list[dict[str, Any]]:
        """Script outcome where only `indices` succeed (others are gaps)."""
        return make_variations(indices, mime_type)


class FakeRunAgent(ScriptedAsyncFake):
    """Fake `helpers.agent.run_agent`, patched as `job_runner_service._run_agent`.

    Default: `{"image_prompt": "Fake prompt for variation <n>"}` (n = call number).
    With `apply_validator=True`, a `str` outcome is passed through the call's
    `validator` like the real `run_agent`: invalid → `AgentValidationError`,
    valid → `ValidationResult.data` (or the raw text if `data` is None).
    """

    PARAMS = (
        "agent", "user_id", "message_text", "image_data", "image_mime_type",
        "validator", "initial_state",
    )

    def __init__(
        self, script: Iterable[Any] | None = None, *, apply_validator: bool = True
    ) -> None:
        super().__init__(script)
        self.apply_validator = apply_validator

    def default(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        return {"image_prompt": f"Fake prompt for variation {self.call_count}"}

    async def _resolve(self, outcome: Any, args: tuple, kwargs: dict[str, Any]) -> Any:
        result = await super()._resolve(outcome, args, kwargs)
        validator = self._bind(args, kwargs).get("validator")
        if self.apply_validator and validator is not None and isinstance(result, str):
            from core.validation import AgentValidationError

            vr = validator(result)
            if not vr.is_valid:
                raise AgentValidationError(
                    f"Validation failed: {'; '.join(vr.errors)}",
                    list(vr.errors),
                    "ad_variant_image_prompter",
                    vr.error_code or "VALIDATION_ERROR",
                )
            return vr.data if vr.data is not None else result
        return result

    @property
    def messages(self) -> list[str]:
        return [c.arguments.get("message_text") for c in self.calls]


class FakeAgent:
    """Opaque agent object returned by FakePrompterFactory."""

    name = "ad_variant_image_prompter"
    tools: list = []


class FakePrompterFactory:
    """Fake `make_ad_variant_image_prompter_agent` (avoids Langfuse/LiteLlm)."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.agents: list[FakeAgent] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def __call__(self, custom_prompt: str | None = None) -> FakeAgent:
        self.calls.append({"custom_prompt": custom_prompt})
        agent = FakeAgent()
        self.agents.append(agent)
        return agent


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LogLine:
    level: str
    message: str
    logger_name: str | None


class LogCapture:
    """Loguru sink capturing every emitted line (TRACE and above)."""

    def __init__(self, level: str | int = "TRACE") -> None:
        self.level = level
        self.records: list[LogLine] = []
        self._handler_id: int | None = None

    def _sink(self, message: Any) -> None:
        record = message.record
        self.records.append(
            LogLine(
                level=record["level"].name,
                message=record["message"],
                logger_name=record["extra"].get("name"),
            )
        )

    def start(self) -> "LogCapture":
        if self._handler_id is None:
            self._handler_id = logger.add(self._sink, level=self.level, format="{message}")
        return self

    def stop(self) -> None:
        if self._handler_id is not None:
            try:
                logger.remove(self._handler_id)
            except ValueError:
                pass
            self._handler_id = None

    def __enter__(self) -> "LogCapture":
        return self.start()

    def __exit__(self, *exc_info: Any) -> None:
        self.stop()

    @property
    def lines(self) -> list[str]:
        return [r.message for r in self.records]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def at_level(self, level: str) -> list[str]:
        return [r.message for r in self.records if r.level == level]

    def contains(self, needle: str) -> bool:
        return any(needle in line for line in self.lines)

    def clear(self) -> None:
        self.records.clear()


# ---------------------------------------------------------------------------
# Attribute patching (tolerant of missing attributes)
# ---------------------------------------------------------------------------


_MISSING = object()


class AttrPatcher:
    """setattr with restore; missing attributes are deleted on undo.

    For classes and modules only the object's own `__dict__` counts as "had the
    attribute", so patching an inherited method (e.g. `socket.socket.connect`)
    is undone by deleting the override instead of pinning the parent's method.
    """

    def __init__(self) -> None:
        self._undo: list[tuple[Any, str, Any]] = []

    def set(self, obj: Any, name: str, value: Any) -> None:
        if isinstance(obj, (type, ModuleType)):
            old = vars(obj).get(name, _MISSING)
        else:
            old = getattr(obj, name, _MISSING)
        self._undo.append((obj, name, old))
        setattr(obj, name, value)

    def set_if_present(self, obj: Any, name: str, value: Any) -> bool:
        if hasattr(obj, name):
            self.set(obj, name, value)
            return True
        return False

    def undo(self) -> None:
        while self._undo:
            obj, name, old = self._undo.pop()
            try:
                if old is _MISSING:
                    delattr(obj, name)
                else:
                    setattr(obj, name, old)
            except (AttributeError, TypeError):
                pass


def _import_optional(dotted: str) -> ModuleType | None:
    try:
        return importlib.import_module(dotted)
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Network guard
# ---------------------------------------------------------------------------


def _uses_real_transport(client: httpx.Client | httpx.AsyncClient, request: httpx.Request) -> bool:
    """True only for httpx's real network transports. MockTransport, ASGI/WSGI
    transports and Starlette's TestClient transport are allowed through."""
    try:
        transport = client._transport_for_url(request.url)
    except AttributeError:  # pragma: no cover - private API changed
        transport = getattr(client, "_transport", None)
    return isinstance(transport, (httpx.HTTPTransport, httpx.AsyncHTTPTransport))


@contextmanager
def network_guard() -> Iterator[None]:
    """Make any real outbound call fail with AssertionError("unmocked network call").

    Patches `httpx.AsyncClient.send`, `httpx.Client.send` and
    `socket.socket.connect`. httpx clients backed by a non-network transport
    (e.g. `httpx.MockTransport`, `TestClient`) keep working.
    """
    patcher = AttrPatcher()
    orig_async_send = httpx.AsyncClient.send
    orig_sync_send = httpx.Client.send

    async def _guarded_async_send(self, request, *args, **kwargs):
        if _uses_real_transport(self, request):
            raise AssertionError(UNMOCKED_NETWORK_MSG)
        return await orig_async_send(self, request, *args, **kwargs)

    def _guarded_sync_send(self, request, *args, **kwargs):
        if _uses_real_transport(self, request):
            raise AssertionError(UNMOCKED_NETWORK_MSG)
        return orig_sync_send(self, request, *args, **kwargs)

    def _blocked_connect(self, *args, **kwargs):
        raise AssertionError(UNMOCKED_NETWORK_MSG)

    try:
        patcher.set(httpx.AsyncClient, "send", _guarded_async_send)
        patcher.set(httpx.Client, "send", _guarded_sync_send)
        patcher.set(socket.socket, "connect", _blocked_connect)
        yield
    finally:
        patcher.undo()


# ---------------------------------------------------------------------------
# patched_pipeline
# ---------------------------------------------------------------------------


@dataclass
class PipelineHarness:
    """Everything patched by `patched_pipeline`, for assertions."""

    redis: FakeRedis
    get_ad_variant_image: FakeGetAdVariantImage
    upload: FakeUploadImageToLibrary
    download: FakeDownloadBaseImage
    edit: FakeEditImageVariations
    run_agent: FakeRunAgent
    prompter_factory: FakePrompterFactory
    sleep: FakeSleep
    logs: LogCapture | None
    settings: Any
    skipped: list[str] = field(default_factory=list)


@contextmanager
def patched_pipeline(
    *,
    redis: FakeRedis | None = None,
    get_ad_variant_image: FakeGetAdVariantImage | None = None,
    upload: FakeUploadImageToLibrary | None = None,
    download: FakeDownloadBaseImage | None = None,
    edit: FakeEditImageVariations | None = None,
    run_agent: FakeRunAgent | None = None,
    prompter_factory: FakePrompterFactory | None = None,
    sleep: FakeSleep | None = None,
    id_base_image: Any = None,
    use_mock_sinergia: bool = False,
    debug: bool = False,
    internal_api_key: str | None = DEFAULT_INTERNAL_API_KEY,
    sinergia_api_key: str | None = DEFAULT_SINERGIA_API_KEY,
    block_network: bool = True,
    capture_logs: bool = True,
    extra_patches: Iterable[tuple[Any, str, Any]] = (),
) -> Iterator[PipelineHarness]:
    """Patch the edit pipeline's collaborators and settings; restore in `finally`.

    Patched (missing attributes are created and later deleted):
      services.job_runner_service: `_redis` (→ FakeRedis), `_download_base_image`,
          `_run_agent`, `_edit_sleep` (→ FakeSleep); plus `edit_image_variations`,
          `get_ad_variant_image`, `upload_image_to_library` and
          `make_ad_variant_image_prompter_agent` only if already module-level names
      agents.nano_banana_agent: `edit_image_variations`
      agents.tools.campaign_tools and agents.tools.mock_sinergia:
          `get_ad_variant_image`, `upload_image_to_library`
      agents.ad_variant_image_prompter_agent: `make_ad_variant_image_prompter_agent`
      settings: USE_MOCK_SINERGIA, DEBUG, FURY_INTERNAL_API_KEY, SINERGIA_SERVICE_API_KEY

    The get fake is linked to the upload fake so ids returned by the upload are
    classified as URL_Resolution calls. Pass `id_base_image` (the request's) to
    fix the Base_Image id when the get fake has none, e.g. when resuming from an
    `upload` / `resolve_urls` checkpoint where no Base_Image call happens.

    `extra_patches` items are `(module_or_dotted_path_or_object, attr, value)`.
    """
    from core.config import settings

    harness = PipelineHarness(
        redis=redis if redis is not None else FakeRedis(),
        get_ad_variant_image=get_ad_variant_image or FakeGetAdVariantImage(),
        upload=upload or FakeUploadImageToLibrary(),
        download=download or FakeDownloadBaseImage(),
        edit=edit or FakeEditImageVariations(),
        run_agent=run_agent or FakeRunAgent(),
        prompter_factory=prompter_factory or FakePrompterFactory(),
        sleep=sleep or FakeSleep(),
        logs=LogCapture() if capture_logs else None,
        settings=settings,
    )
    harness.get_ad_variant_image.link_upload(harness.upload)
    if id_base_image is not None and harness.get_ad_variant_image.base_image_id is None:
        harness.get_ad_variant_image.base_image_id = str(id_base_image)
    patcher = AttrPatcher()

    with ExitStack() as stack:
        try:
            if block_network:
                stack.enter_context(network_guard())
            if harness.logs is not None:
                stack.enter_context(harness.logs)

            # settings
            patcher.set(settings, "USE_MOCK_SINERGIA", use_mock_sinergia)
            patcher.set(settings, "DEBUG", debug)
            patcher.set(settings, "FURY_INTERNAL_API_KEY", internal_api_key)
            patcher.set(settings, "SINERGIA_SERVICE_API_KEY", sinergia_api_key)

            # services.job_runner_service (required)
            jrs = importlib.import_module(_JOB_RUNNER)
            fake_redis = harness.redis
            patcher.set(jrs, "_redis", lambda: fake_redis)
            patcher.set(jrs, "_download_base_image", harness.download)
            patcher.set(jrs, "_run_agent", harness.run_agent)
            # Created if missing (deleted on exit), so the pipeline never waits.
            patcher.set(jrs, "_edit_sleep", harness.sleep)
            for name, fake in (
                ("edit_image_variations", harness.edit),
                ("get_ad_variant_image", harness.get_ad_variant_image),
                ("upload_image_to_library", harness.upload),
                ("make_ad_variant_image_prompter_agent", harness.prompter_factory),
            ):
                patcher.set_if_present(jrs, name, fake)

            # agents.* (optional modules: lazy imports read these at call time)
            targets: tuple[tuple[str, tuple[tuple[str, Any], ...]], ...] = (
                (_NANO_BANANA, (("edit_image_variations", harness.edit),)),
                (_CAMPAIGN_TOOLS, (
                    ("get_ad_variant_image", harness.get_ad_variant_image),
                    ("upload_image_to_library", harness.upload),
                )),
                (_MOCK_SINERGIA, (
                    ("get_ad_variant_image", harness.get_ad_variant_image),
                    ("upload_image_to_library", harness.upload),
                )),
                (_PROMPTER_AGENT, (
                    ("make_ad_variant_image_prompter_agent", harness.prompter_factory),
                )),
            )
            for dotted, attrs in targets:
                module = _import_optional(dotted)
                if module is None:
                    harness.skipped.append(dotted)
                    continue
                for name, fake in attrs:
                    patcher.set(module, name, fake)

            for target, name, value in extra_patches:
                obj = importlib.import_module(target) if isinstance(target, str) else target
                patcher.set(obj, name, value)

            yield harness
        finally:
            patcher.undo()
