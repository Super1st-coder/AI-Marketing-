"""Shared fakes for the adset-creative-diversity tests (not a test module).

Used by tests/test_phase1_legacy_golden.py, tests/test_adset_diversity_pipeline*.py
and tests/test_nano_banana_generation*.py to run
`services.job_runner_service._run_phase1` (Legacy_Path and Diversity_Path) and
`agents.nano_banana_agent.generate_images_from_prompts` fully in memory: no
Redis, no Sinergia, no Abyssale, no Gemini, no Langfuse, no LLM, no network
and no real waits (Req 12.1, 12.2).

Reused from tests/_edit_pipeline_fakes.py:
    FakeRedis, ScriptedAsyncFake, LogCapture, network_guard(), AttrPatcher,
    FakeTask, Call, DEFAULT, cp_key

Contents:
    FakeRunAgent               helpers.agent.run_agent (as `_run_agent`): responses
                               per agent name, (agent_name, message) log, runs the
                               `validator` it receives like the real run_agent
    FakeAgent / FakeAgentFactories
                               make_<agent>_agent factories without Langfuse
    FakeGetAdsetContext        get_adset_context(id_adset)
    FakeGetTemplateContext     get_template_context(project_id)
    FakeGetATemplateDefinition get_a_template_definition(template_id)
    FakeGetCtas                get_ctas()
    FakeSaveAds                save_ads(id_adset, id_ad, payloads)
    FakeDeleteVariants         delete_variants(variant_ids)
    FakePostToAbyssaleAndWait  abyssale_tools.post_to_abyssale_and_wait(...)
    FakeGenerateImagesFromPrompts
                               nano_banana_agent.generate_images_from_prompts(...)
    FakeUploadImageToLibraryTool
                               nano_banana_agent.upload_image_to_library_tool
    FakeGenaiClientFactory     google.genai.Client (sync generate_content)
    FakeHttpxGet / FakeHttpResponse
                               httpx.get (Image_Generator downloads)
    FakeAsyncSleep             asyncio.sleep (records seconds, never waits)
    CallSpy                    spy around a real sync function (assign_territories)
    make_adset_context(ad_ids) copy.deepcopy(_MOCK_ADSET) with Ads in adset.data.ads
    image_elements_from_message / conformant_image_prompts / expected_image_elements
                               P15 helpers (Image_Elements line, conforming
                               Image_Prompter response, expected ids)
    patched_diversity_pipeline(...)
                               patches job_runner_service (`_run_agent`, `_redis`,
                               `_load`, `_store`), the factories, the tools and
                               settings; restores everything on exit

Script outcomes (all scripted fakes, same rules as _edit_pipeline_fakes):
    - an exception instance or class  -> raised
    - a callable                      -> called with the call's (*args, **kwargs);
                                         awaited if it returns an awaitable
    - DEFAULT                         -> the fake's default behaviour
    - any other value                 -> returned (deep-copied)
When the script is exhausted the default behaviour is used.

FakeRunAgent outcomes follow the same rules, except that a callable receives a
single `AgentCall` argument.
"""
from __future__ import annotations

import asyncio
import base64
import copy
import importlib
import inspect
import itertools
import json
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

import httpx

from tests._edit_pipeline_fakes import (  # noqa: F401  (re-exported)
    CHECKPOINT_TTL,
    DEFAULT,
    DEFAULT_IMAGE_BYTES,
    DEFAULT_TASK_ID,
    UNMOCKED_NETWORK_MSG,
    AttrPatcher,
    Call,
    FakeRedis,
    FakeTask,
    LogCapture,
    ScriptedAsyncFake,
    _import_optional,
    cp_key,
    network_guard,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_JOB_RUNNER = "services.job_runner_service"
_NANO_BANANA = "agents.nano_banana_agent"
_CAMPAIGN_TOOLS = "agents.tools.campaign_tools"
_MOCK_SINERGIA = "agents.tools.mock_sinergia"
_ABYSSALE_TOOLS = "agents.tools.abyssale_tools"
_TERRITORY = "services.territory_assignment"
_GENAI = "google.genai"

# Agent names, as set by each factory (`Agent(name=...)`).
ESTRATEGA = "estratega_agent"
ESTRATEGA_ADSET = "estratega_adset_agent"
COPYWRITER = "copywriter_agent"
IMAGE_PROMPTER = "image_prompter_agent"
VALIDADOR = "validador_agent"
VALIDADOR_ADSET = "validador_adset_agent"
DATA_COLLECTOR = "data_collector_agent"
NANO_BANANA = "nano_banana_agent"
TEMPLATE_MAPPER = "template_mapper_agent"

# agent name -> (module, factory attribute)
FACTORY_TARGETS: dict[str, tuple[str, str]] = {
    ESTRATEGA: ("agents.estratega_agent", "make_estratega_agent"),
    ESTRATEGA_ADSET: ("agents.estratega_adset_agent", "make_estratega_adset_agent"),
    COPYWRITER: ("agents.copywriter_agent", "make_copywriter_agent"),
    IMAGE_PROMPTER: ("agents.image_prompter_agent", "make_image_prompter_agent"),
    VALIDADOR: ("agents.validador_agent", "make_validador_agent"),
    VALIDADOR_ADSET: ("agents.validador_adset_agent", "make_validador_adset_agent"),
    DATA_COLLECTOR: ("agents.data_collector_agent", "make_data_collector_agent"),
    NANO_BANANA: ("agents.nano_banana_agent", "make_nano_banana_agent"),
    TEMPLATE_MAPPER: ("agents.template_mapper_agent", "make_template_mapper_agent"),
}

# Sinergia tools patched in both mock_sinergia and campaign_tools.
SINERGIA_TOOL_NAMES: tuple[str, ...] = (
    "get_adset_context",
    "get_template_context",
    "get_a_template_definition",
    "get_ctas",
    "save_ads",
    "delete_variants",
)

DEFAULT_GENERATED_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-generated-image-bytes"
DEFAULT_PROJECT_ID = "test-project-id"

# Captured before any patching so FakeAsyncSleep can still yield to the loop.
_REAL_ASYNCIO_SLEEP = asyncio.sleep


def data_uri(data: bytes = DEFAULT_GENERATED_IMAGE_BYTES, mime_type: str = "image/png") -> str:
    """`data:<mime>;base64,<...>` URI, the shape generate_images_from_prompts produces."""
    return f"data:{mime_type};base64,{base64.b64encode(data).decode()}"


def _mock_sinergia():
    return importlib.import_module(_MOCK_SINERGIA)


def mock_templates() -> dict[str, Any]:
    """Deep copy of `mock_sinergia._MOCK_TEMPLATES` (`{"ok": True, "templates": [...]}`)."""
    return copy.deepcopy(_mock_sinergia()._MOCK_TEMPLATES)


def mock_template_ids() -> list[str]:
    return [str(t.get("id")) for t in mock_templates().get("templates", []) if t.get("id")]


def expected_template_order(task_id: str, templates: Sequence[str] | None = None) -> list[str]:
    """Template order the Diversity_Path should use for `task_id` (Req 12.2, 12.19, 12.20).

    Delegates to `services.adset_diversity.template_order` so tests and code share
    the same function; defaults to the mock project's template ids.
    """
    from services.adset_diversity import template_order  # lazy: keep fakes import-light

    return template_order(list(templates) if templates else mock_template_ids(), task_id)


def expected_slots(plan_id: str, n: int, template: Any) -> list[dict[str, Any]]:
    """Variant_Slots the Diversity_Path should build for a plan (Req 12.2, 12.22, 12.25).

    Delegates to `services.adset_diversity.assign_variant_angles` so tests and code
    share the same function: `[{"variant_key": f"{plan_id}_v{k}", "template_id":
    template, "angle": angles[k-1]} for k in 1..n]`.
    """
    from services.adset_diversity import assign_variant_angles  # lazy: keep fakes import-light

    angles = assign_variant_angles(plan_id, n)
    return [
        {"variant_key": f"{plan_id}_v{k}", "template_id": template, "angle": angles[k - 1]}
        for k in range(1, n + 1)
    ]


IMAGE_ELEMENTS_PREFIX = "Image_Elements: "


def image_elements_from_message(message: Any) -> dict[str, Any] | None:
    """Parsed `Image_Elements: {json}` line of an Image_Prompter message (P15, Req 12.2).

    The line is produced by `services.adset_diversity.build_image_prompt_message`
    (`{"template_id", "elements": [{"element_id", "width"?, "height"?}],
    "preview_url"?}`). Returns `None` when the message is not a `str` or has no
    such line (Properties 13/16 harnesses, Legacy_Path).
    """
    if not isinstance(message, str):
        return None
    for line in message.splitlines():
        if line.startswith(IMAGE_ELEMENTS_PREFIX):
            return json.loads(line[len(IMAGE_ELEMENTS_PREFIX):])
    return None


def _element_ids(element_ids: Iterable[Any] | None) -> list[str]:
    """`element_ids` as `str` ids: accepts ids or the `elements` dicts of the line."""
    ids: list[str] = []
    for e in element_ids or ():
        ids.append(str(e["element_id"]) if isinstance(e, Mapping) else str(e))
    return ids


def conformant_image_prompts(
    slots: Iterable[Mapping[str, Any]], element_ids: Iterable[Any] | None
) -> list[dict[str, Any]]:
    """Image_Prompter response conforming to P15 for `slots` (Req 12.2, 12.29).

    One item per Variant_Slot (`plan_id` = slot's `plan_id` or its `variant_key`
    without the `_v<k>` suffix, `variant_key`, `template_id`) whose `image_prompts`
    has exactly one entry per Element_Id (`element_id`, `element_type: "image"`,
    `image_prompt`, `image_request`). `element_ids` may be a list of `str` or the
    `elements` dicts of `image_elements_from_message(...)`; empty → `image_prompts: []`.
    """
    ids = _element_ids(element_ids)
    result: list[dict[str, Any]] = []
    for s in slots:
        variant_key = s["variant_key"]
        plan_id = s.get("plan_id") or str(variant_key).rsplit("_v", 1)[0]
        result.append({
            "plan_id": plan_id,
            "variant_key": variant_key,
            "template_id": s.get("template_id"),
            "image_prompts": [
                {
                    "element_id": element_id,
                    "element_type": "image",
                    "image_prompt": f"scene {variant_key} {element_id}",
                    "image_request": "y",
                }
                for element_id in ids
            ],
        })
    return result


def expected_image_elements(template: Any) -> list[str]:
    """Image_Elements the Diversity_Path should resolve for `template` (P15, Req 12.29).

    Delegates to `services.adset_diversity.template_image_elements` with
    `DEFAULT_DECORATIVE_IMAGE_PATTERNS`, so expected ids are never written by hand.
    """
    from services.adset_diversity import (  # lazy: keep fakes import-light
        DEFAULT_DECORATIVE_IMAGE_PATTERNS,
        template_image_elements,
    )

    return template_image_elements(template, DEFAULT_DECORATIVE_IMAGE_PATTERNS)


def mock_ctas() -> list[str]:
    return list(_mock_sinergia()._MOCK_CTAS)


# ---------------------------------------------------------------------------
# Adset context
# ---------------------------------------------------------------------------


def make_ad(ad_id: Any, **extra: Any) -> dict[str, Any]:
    """Minimal Ad entry for `adset.data.ads`."""
    return {"id": ad_id, "name": f"Ad {ad_id}", **extra}


def make_adset_context(
    ad_ids: Iterable[Any] = (),
    *,
    base: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """`copy.deepcopy(_MOCK_ADSET)` (or of `base`) with Ads added in `adset.data.ads`.

    Each item of `ad_ids` is either a dict (used as the Ad entry, deep-copied)
    or any other value (wrapped with `make_ad`, kept as-is so tests can pass
    invalid ids such as `0`, `-1`, `"x"`, `True` or `None`). With no `ad_ids`
    the `ads` list is empty (the mock has none).
    """
    ctx = copy.deepcopy(dict(base) if base is not None else _mock_sinergia()._MOCK_ADSET)
    adset = ctx.setdefault("adset", {})
    data = adset.get("data") if isinstance(adset.get("data"), dict) else adset
    data["ads"] = [
        copy.deepcopy(a) if isinstance(a, dict) else make_ad(a) for a in ad_ids
    ]
    return ctx


def adset_ads(ctx: Mapping[str, Any]) -> list[Any]:
    """The `ads` list of a context built by `make_adset_context`."""
    adset = ctx.get("adset", {})
    data = adset.get("data") if isinstance(adset.get("data"), dict) else adset
    return data.get("ads", [])


# ---------------------------------------------------------------------------
# Shared event log (call order across fakes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    name: str
    arguments: dict[str, Any]


class EventLog(list):
    """Ordered log of tool calls shared by the fakes (e.g. Abyssale vs delete_variants)."""

    @property
    def names(self) -> list[str]:
        return [e.name for e in self]

    def index_of(self, name: str, occurrence: int = 0) -> int:
        """Position of the `occurrence`-th event called `name` (ValueError if absent)."""
        seen = 0
        for i, e in enumerate(self):
            if e.name == name:
                if seen == occurrence:
                    return i
                seen += 1
        raise ValueError(f"event {name!r} #{occurrence} not recorded")

    def of(self, name: str) -> list[Event]:
        return [e for e in self if e.name == name]


class _EventedFake(ScriptedAsyncFake):
    """ScriptedAsyncFake that also appends an Event to a shared EventLog."""

    NAME = "fake"

    def __init__(self, script: Iterable[Any] | None = None) -> None:
        super().__init__(script)
        self.events: EventLog | None = None

    def bind_events(self, events: EventLog) -> "_EventedFake":
        self.events = events
        return self

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.events is not None:
            self.events.append(Event(self.NAME, self._bind(args, kwargs)))
        return await super().__call__(*args, **kwargs)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


@dataclass
class FakeAgent:
    """Opaque agent returned by the fake factories; `name` drives FakeRunAgent."""

    name: str
    custom_prompt: str | None = None
    tools: list = field(default_factory=list)


class FakeAgentFactory:
    """Fake `make_<agent>_agent(custom_prompt=None)` (no Langfuse / LiteLlm)."""

    def __init__(self, name: str, owner: "FakeAgentFactories | None" = None) -> None:
        self.name = name
        self.owner = owner
        self.calls: list[dict[str, Any]] = []
        self.agents: list[FakeAgent] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def custom_prompts(self) -> list[str | None]:
        return [c["custom_prompt"] for c in self.calls]

    def __call__(self, *args: Any, **kwargs: Any) -> FakeAgent:
        custom_prompt = kwargs.get("custom_prompt", args[0] if args else None)
        call = {"args": args, "kwargs": dict(kwargs), "custom_prompt": custom_prompt}
        self.calls.append(call)
        if self.owner is not None:
            self.owner.calls.append((self.name, custom_prompt))
        agent = FakeAgent(name=self.name, custom_prompt=custom_prompt)
        self.agents.append(agent)
        return agent


class FakeAgentFactories:
    """One FakeAgentFactory per entry of FACTORY_TARGETS.

    `calls` keeps `(agent_name, custom_prompt)` for every factory call, in order.
    """

    def __init__(self, names: Iterable[str] = tuple(FACTORY_TARGETS)) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.factories: dict[str, FakeAgentFactory] = {
            n: FakeAgentFactory(n, owner=self) for n in names
        }

    def __getitem__(self, name: str) -> FakeAgentFactory:
        return self.factories[name]

    def count(self, name: str) -> int:
        return self.factories[name].call_count

    def custom_prompts(self, name: str) -> list[str | None]:
        return self.factories[name].custom_prompts


@dataclass
class AgentCall:
    """One `_run_agent` invocation recorded by FakeRunAgent."""

    agent_name: str
    agent: Any
    user_id: str
    message: str
    validator: Callable | None
    image_data: Any = None
    image_mime_type: Any = None
    initial_state: Any = None
    index: int = 0  # call number for this agent name (0-based)


class FakeRunAgent:
    """Fake `helpers.agent.run_agent`, patched as `job_runner_service._run_agent`.

    `responses`: `{agent_name: [outcome, ...]}` consumed in order per agent.
    `defaults`:  `{agent_name: outcome}` used every time once that agent's
                 queue is empty (a callable gets the `AgentCall`).
    With neither, the call fails with AssertionError (`strict=True`) or returns
    `""` (`strict=False`).

    Like the real run_agent, when the call has a `validator` and
    `run_validator=True`, the response (JSON-serialised if it is not a `str`)
    is passed to it: invalid → `AgentValidationError(step=agent_name,
    code=error_code)`; valid → `ValidationResult.data`, or the text when
    `data` is None.
    """

    def __init__(
        self,
        responses: Mapping[str, Iterable[Any]] | None = None,
        *,
        defaults: Mapping[str, Any] | None = None,
        run_validator: bool = True,
        strict: bool = True,
    ) -> None:
        self.responses: dict[str, list[Any]] = {
            k: list(v) for k, v in (responses or {}).items()
        }
        self.defaults: dict[str, Any] = dict(defaults or {})
        self.run_validator = run_validator
        self.strict = strict
        self.calls: list[AgentCall] = []
        self.results: list[Any] = []

    # -- configuration -------------------------------------------------------
    def push(self, agent_name: str, *outcomes: Any) -> "FakeRunAgent":
        self.responses.setdefault(agent_name, []).extend(outcomes)
        return self

    def set_default(self, agent_name: str, outcome: Any) -> "FakeRunAgent":
        self.defaults[agent_name] = outcome
        return self

    # -- call ------------------------------------------------------------------
    async def __call__(
        self,
        agent: Any,
        user_id: str,
        message_text: str,
        image_data: Any = None,
        image_mime_type: Any = None,
        validator: Callable | None = None,
        initial_state: Any = None,
        **_extra: Any,  # e.g. `usage=` (token meter of the Legacy_Path): accepted, ignored
    ) -> Any:
        name = getattr(agent, "name", None) or type(agent).__name__
        call = AgentCall(
            agent_name=name,
            agent=agent,
            user_id=user_id,
            message=message_text,
            validator=validator,
            image_data=image_data,
            image_mime_type=image_mime_type,
            initial_state=initial_state,
            index=self.count(name),
        )
        self.calls.append(call)
        queue = self.responses.get(name)
        if queue:
            outcome = queue.pop(0)
        elif name in self.defaults:
            outcome = self.defaults[name]
        elif self.strict:
            raise AssertionError(f"FakeRunAgent: no scripted response for agent {name!r}")
        else:
            outcome = ""
        result = await self._resolve(outcome, call)
        if self.run_validator and validator is not None:
            result = self._validate(name, validator, result)
        self.results.append(result)
        return result

    @staticmethod
    async def _resolve(outcome: Any, call: AgentCall) -> Any:
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, type) and issubclass(outcome, BaseException):
            raise outcome()
        if callable(outcome):
            result = outcome(call)
            if inspect.isawaitable(result):
                result = await result
            return result
        return copy.deepcopy(outcome)

    @staticmethod
    def _validate(name: str, validator: Callable, result: Any) -> Any:
        from core.validation import AgentValidationError

        text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        vr = validator(text)
        if not vr.is_valid:
            raise AgentValidationError(
                message=f"Validation failed for agent {name}",
                errors=vr.errors,
                step=name,
                code=getattr(vr, "error_code", "VALIDATION_ERROR"),
            )
        return vr.data if vr.data is not None else text

    # -- views -------------------------------------------------------------------
    @property
    def sequence(self) -> list[tuple[str, str]]:
        """`(agent_name, message)` of every call, in order."""
        return [(c.agent_name, c.message) for c in self.calls]

    @property
    def agent_names(self) -> list[str]:
        return [c.agent_name for c in self.calls]

    def calls_for(self, agent_name: str) -> list[AgentCall]:
        return [c for c in self.calls if c.agent_name == agent_name]

    def messages_for(self, agent_name: str) -> list[str]:
        return [c.message for c in self.calls_for(agent_name)]

    def count(self, agent_name: str) -> int:
        return sum(1 for c in self.calls if c.agent_name == agent_name)

    @property
    def call_count(self) -> int:
        return len(self.calls)


# ---------------------------------------------------------------------------
# Sinergia tools
# ---------------------------------------------------------------------------


class FakeGetAdsetContext(_EventedFake):
    """Fake `get_adset_context(id_adset)`. Default: deep copy of `context`
    (default `make_adset_context()`, i.e. the mock without Ads)."""

    NAME = "get_adset_context"
    PARAMS = ("id_adset",)

    def __init__(
        self, context: Mapping[str, Any] | None = None, script: Iterable[Any] | None = None
    ) -> None:
        super().__init__(script)
        self.context = copy.deepcopy(dict(context)) if context is not None else make_adset_context()

    def default(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return copy.deepcopy(self.context)


class FakeGetTemplateContext(_EventedFake):
    """Fake `get_template_context(project_id)`. Default: `{"ok": True, "templates": [...]}`
    with `templates` (default the 3 templates of `_MOCK_TEMPLATES`)."""

    NAME = "get_template_context"
    PARAMS = ("project_id",)

    def __init__(
        self, templates: Iterable[Mapping[str, Any]] | None = None,
        script: Iterable[Any] | None = None,
    ) -> None:
        super().__init__(script)
        self.templates: list[dict[str, Any]] = (
            [copy.deepcopy(dict(t)) for t in templates]
            if templates is not None else mock_templates()["templates"]
        )

    def default(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "templates": copy.deepcopy(self.templates)}


class FakeGetATemplateDefinition(_EventedFake):
    """Fake `get_a_template_definition(template_id)`, with the real tool's shape:
    `{"ok": True, "template": {...}}` if found, `{"ok": False, "error": ...}` otherwise."""

    NAME = "get_a_template_definition"
    PARAMS = ("template_id",)

    def __init__(
        self, templates: Iterable[Mapping[str, Any]] | None = None,
        script: Iterable[Any] | None = None,
    ) -> None:
        super().__init__(script)
        self.templates: list[dict[str, Any]] = (
            [copy.deepcopy(dict(t)) for t in templates]
            if templates is not None else mock_templates()["templates"]
        )

    def default(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        template_id = str(self._bind(args, kwargs).get("template_id"))
        for t in self.templates:
            if str(t.get("id")) == template_id:
                return {"ok": True, "template": copy.deepcopy(t)}
        return {"ok": False, "error": "template not found"}


class FakeGetCtas(_EventedFake):
    """Fake `get_ctas()`. Default: `ctas` (default `_MOCK_CTAS`)."""

    NAME = "get_ctas"

    def __init__(self, ctas: Iterable[str] | None = None, script: Iterable[Any] | None = None) -> None:
        super().__init__(script)
        self.ctas: list[str] = list(ctas) if ctas is not None else mock_ctas()

    def default(self, *args: Any, **kwargs: Any) -> list[str]:
        return list(self.ctas)


class FakeSaveAds(_EventedFake):
    """Fake `save_ads(id_adset, id_ad, payloads)`.

    Default: Sinergia-shaped success with one created id per payload
    (`{"ok": True, "ads": {"ok": True, "data": {..., "created": [{"id": n}, ...]}}}`),
    ids unique across calls starting at `first_id`.
    """

    NAME = "save_ads"
    PARAMS = ("id_adset", "id_ad", "payloads")

    def __init__(self, script: Iterable[Any] | None = None, *, first_id: int = 5001) -> None:
        super().__init__(script)
        self._ids = itertools.count(first_id)
        self.created_ids: list[list[int]] = []

    def default(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        bound = self._bind(args, kwargs)
        payloads = bound.get("payloads") or []
        ids = [next(self._ids) for _ in payloads]
        self.created_ids.append(ids)
        return {
            "ok": True,
            "ads": {
                "ok": True,
                "data": {
                    "ad_set_id": bound.get("id_adset"),
                    "ad_id": bound.get("id_ad"),
                    "created": [{"id": i} for i in ids],
                },
            },
        }

    @property
    def payloads(self) -> list[list[dict[str, Any]]]:
        """`payloads` argument of each call."""
        return [c.arguments.get("payloads") for c in self.calls]

    @property
    def ad_ids(self) -> list[Any]:
        return [c.arguments.get("id_ad") for c in self.calls]


class FakeDeleteVariants(_EventedFake):
    """Fake `delete_variants(variant_ids)`. Default: `True`."""

    NAME = "delete_variants"
    PARAMS = ("variant_ids",)

    def default(self, *args: Any, **kwargs: Any) -> bool:
        return True

    @property
    def variant_ids(self) -> list[Any]:
        return [c.arguments.get("variant_ids") for c in self.calls]


class FakeUploadImageToLibraryTool(_EventedFake):
    """Fake Upload_Tool as imported by nano_banana_agent (`upload_image_to_library_tool`).

    Default: unique non-empty id per call (`IMG_fake_<ad_id>_<n>`). Script
    outcomes may be `""`, other values or exceptions.
    """

    NAME = "upload_image_to_library"
    PARAMS = ("ad_id", "image_data")

    def __init__(self, script: Iterable[Any] | None = None) -> None:
        super().__init__(script)
        self._counter = itertools.count(1)

    def default(self, *args: Any, **kwargs: Any) -> str:
        return f"IMG_fake_{self._bind(args, kwargs).get('ad_id', 'x')}_{next(self._counter)}"

    @property
    def payloads(self) -> list[dict[str, Any]]:
        """`image_data` dict of each call (keys sent to Sinergia)."""
        return [c.arguments.get("image_data") for c in self.calls]

    @property
    def uploaded_ids(self) -> list[str]:
        return [r for r in self.results if isinstance(r, str) and r.strip()]


# ---------------------------------------------------------------------------
# Abyssale and Image_Generator
# ---------------------------------------------------------------------------


class FakePostToAbyssaleAndWait(_EventedFake):
    """Fake `post_to_abyssale_and_wait(job_id, abyssale_payload, id_adset, ad_id)`.

    Default: `{"ok": True, "status": "WAITING_ABYSSALE", "batch_id":
    "fake-batch-<ad_id>-<n>", "abyssale_response": []}`.
    """

    NAME = "post_to_abyssale_and_wait"
    PARAMS = ("job_id", "abyssale_payload", "id_adset", "ad_id")

    def __init__(self, script: Iterable[Any] | None = None) -> None:
        super().__init__(script)
        self._counter = itertools.count(1)

    def default(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        ad_id = self._bind(args, kwargs).get("ad_id")
        return {
            "ok": True,
            "status": "WAITING_ABYSSALE",
            "batch_id": f"fake-batch-{ad_id}-{next(self._counter)}",
            "abyssale_response": [],
        }

    @property
    def payloads(self) -> list[dict[str, Any]]:
        return [c.arguments.get("abyssale_payload") for c in self.calls]

    @property
    def batch_ids(self) -> list[Any]:
        return [r.get("batch_id") for r in self.results if isinstance(r, dict)]


class FakeGenerateImagesFromPrompts(_EventedFake):
    """Fake `generate_images_from_prompts(image_prompts, ad_id, upload_image_to_library=True)`.

    Default: a deep copy of `image_prompts` where every item of each entry's
    `image_prompts` gets `image_url` (data URI), `image_mime_type` and, when
    uploading, a unique `image_id`; returns `{"ok": True, "generated_images": [...]}`.
    """

    NAME = "generate_images_from_prompts"
    PARAMS = ("image_prompts", "ad_id", "upload_image_to_library")

    def __init__(self, script: Iterable[Any] | None = None) -> None:
        super().__init__(script)
        self._counter = itertools.count(1)

    def default(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        bound = self._bind(args, kwargs)
        upload = bound.get("upload_image_to_library", True)
        generated = copy.deepcopy(bound.get("image_prompts") or [])
        for entry in generated:
            if not isinstance(entry, dict):
                continue
            for item in entry.get("image_prompts") or []:
                if not isinstance(item, dict):
                    continue
                item["image_url"] = data_uri()
                item["image_mime_type"] = "image/png"
                if upload:
                    item["image_id"] = f"IMG_fake_{bound.get('ad_id')}_{next(self._counter)}"
        return {"ok": True, "generated_images": generated}


def _resolve_sync(outcome: Any, default: Callable[..., Any], args: tuple, kwargs: dict) -> Any:
    """Synchronous counterpart of ScriptedAsyncFake._resolve."""
    if outcome is DEFAULT:
        return default(*args, **kwargs)
    if isinstance(outcome, BaseException):
        raise outcome
    if isinstance(outcome, type) and issubclass(outcome, BaseException):
        raise outcome()
    if callable(outcome):
        return outcome(*args, **kwargs)
    return copy.deepcopy(outcome)


def make_genai_image_response(
    data: bytes = DEFAULT_GENERATED_IMAGE_BYTES, mime_type: str = "image/png"
) -> SimpleNamespace:
    """Gemini response with one image part (`candidates[0].content.parts[0].inline_data`)."""
    part = SimpleNamespace(inline_data=SimpleNamespace(data=data, mime_type=mime_type), text=None)
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])


def make_genai_text_response(text: str = "no image") -> SimpleNamespace:
    """Gemini response without `inline_data` (→ "NoImageInResponse")."""
    part = SimpleNamespace(inline_data=None, text=text)
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])


def make_genai_empty_response() -> SimpleNamespace:
    """Gemini response with no candidates."""
    return SimpleNamespace(candidates=[])


class _FakeGenaiModels:
    def __init__(self, owner: "FakeGenaiClientFactory") -> None:
        self._owner = owner

    def generate_content(self, *args: Any, **kwargs: Any) -> Any:
        return self._owner._generate_content(*args, **kwargs)


class FakeGenaiClient:
    """Client returned by FakeGenaiClientFactory (`client.models.generate_content`)."""

    def __init__(self, owner: "FakeGenaiClientFactory", init_kwargs: dict[str, Any]) -> None:
        self.init_kwargs = init_kwargs
        self.models = _FakeGenaiModels(owner)


class FakeGenaiClientFactory:
    """Fake `google.genai.Client` (Gemini_Image_Call).

    `client_script`: outcomes for each `Client(...)` construction (exception →
    construction fails; DEFAULT → a FakeGenaiClient).
    `script`: outcomes for each `generate_content(...)` call (synchronous; it
    runs inside `asyncio.to_thread`). Default: `make_genai_image_response()`.
    Raising `asyncio.TimeoutError` simulates a timeout without waiting.
    """

    def __init__(
        self,
        script: Iterable[Any] | None = None,
        *,
        client_script: Iterable[Any] | None = None,
    ) -> None:
        self.script: list[Any] = list(script or [])
        self.client_script: list[Any] = list(client_script or [])
        self.client_inits: list[dict[str, Any]] = []
        self.clients: list[FakeGenaiClient] = []
        self.generate_calls: list[dict[str, Any]] = []
        self.generate_results: list[Any] = []

    def push(self, *outcomes: Any) -> "FakeGenaiClientFactory":
        self.script.extend(outcomes)
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> FakeGenaiClient:
        self.client_inits.append(dict(kwargs))
        outcome = self.client_script.pop(0) if self.client_script else DEFAULT
        client = _resolve_sync(
            outcome, lambda *a, **k: FakeGenaiClient(self, dict(k)), args, kwargs
        )
        self.clients.append(client)
        return client

    def _generate_content(self, *args: Any, **kwargs: Any) -> Any:
        self.generate_calls.append({"args": args, "kwargs": dict(kwargs)})
        outcome = self.script.pop(0) if self.script else DEFAULT
        result = _resolve_sync(outcome, lambda *a, **k: make_genai_image_response(), args, kwargs)
        self.generate_results.append(result)
        return result

    @property
    def client_count(self) -> int:
        return len(self.client_inits)

    @property
    def generate_count(self) -> int:
        return len(self.generate_calls)


@dataclass
class FakeHttpResponse:
    """Minimal `httpx.Response` stand-in for `httpx.get`."""

    status_code: int = 200
    content: bytes = DEFAULT_IMAGE_BYTES
    headers: dict[str, str] = field(default_factory=lambda: {"content-type": "image/png"})

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"status {self.status_code}",
                request=httpx.Request("GET", "https://fake.invalid/"),
                response=httpx.Response(self.status_code),
            )


class FakeHttpxGet:
    """Fake `httpx.get(url, **kwargs)` (sync; called through `asyncio.to_thread`).

    `by_url`: `{url: [outcome, ...]}` consumed per URL; otherwise `script`
    (global, in order); otherwise the default `FakeHttpResponse()` (200, PNG bytes).
    """

    def __init__(
        self,
        script: Iterable[Any] | None = None,
        *,
        by_url: Mapping[str, Iterable[Any]] | None = None,
    ) -> None:
        self.script: list[Any] = list(script or [])
        self.by_url: dict[str, list[Any]] = {k: list(v) for k, v in (by_url or {}).items()}
        self.calls: list[dict[str, Any]] = []
        self.results: list[Any] = []

    def __call__(self, url: Any, *args: Any, **kwargs: Any) -> Any:
        self.calls.append({"url": str(url), "args": args, "kwargs": dict(kwargs)})
        pending = self.by_url.get(str(url))
        if pending:
            outcome = pending.pop(0)
        elif self.script:
            outcome = self.script.pop(0)
        else:
            outcome = DEFAULT
        result = _resolve_sync(outcome, lambda *a, **k: FakeHttpResponse(), (url, *args), kwargs)
        self.results.append(result)
        return result

    @property
    def urls(self) -> list[str]:
        return [c["url"] for c in self.calls]

    @property
    def call_count(self) -> int:
        return len(self.calls)


class FakeAsyncSleep:
    """Fake `asyncio.sleep`: records the seconds and only yields (`sleep(0)`)."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, delay: float = 0, result: Any = None, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(delay)
        await _REAL_ASYNCIO_SLEEP(0)
        return result

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def total(self) -> float:
        return float(sum(self.calls))


class CallSpy:
    """Transparent wrapper around a sync function that records every call."""

    def __init__(self, fn: Callable[..., Any]) -> None:
        self.fn = fn
        self.calls: list[dict[str, Any]] = []
        self.results: list[Any] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append({"args": args, "kwargs": dict(kwargs)})
        result = self.fn(*args, **kwargs)
        self.results.append(result)
        return result

    @property
    def call_count(self) -> int:
        return len(self.calls)


# ---------------------------------------------------------------------------
# Settings patching (works whether or not the field exists yet)
# ---------------------------------------------------------------------------


_MISSING = object()


class SettingsPatcher:
    """Overrides attributes of the pydantic `settings` object via its `__dict__`.

    Works for declared fields and for fields another task has not added yet
    (e.g. USE_ADSET_CREATIVE_DIVERSITY); undo restores or removes them.
    """

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self._undo: list[tuple[str, Any]] = []

    def set(self, name: str, value: Any) -> None:
        self._undo.append((name, self.settings.__dict__.get(name, _MISSING)))
        object.__setattr__(self.settings, name, value)

    def undo(self) -> None:
        while self._undo:
            name, old = self._undo.pop()
            if old is _MISSING:
                self.settings.__dict__.pop(name, None)
            else:
                object.__setattr__(self.settings, name, old)


# ---------------------------------------------------------------------------
# patched_diversity_pipeline
# ---------------------------------------------------------------------------


@dataclass
class DiversityHarness:
    """Everything patched by `patched_diversity_pipeline`, for assertions."""

    redis: FakeRedis
    run_agent: FakeRunAgent
    factories: FakeAgentFactories
    get_adset_context: FakeGetAdsetContext
    get_template_context: FakeGetTemplateContext
    get_a_template_definition: FakeGetATemplateDefinition
    get_ctas: FakeGetCtas
    save_ads: FakeSaveAds
    delete_variants: FakeDeleteVariants
    post_to_abyssale: FakePostToAbyssaleAndWait
    generate_images: FakeGenerateImagesFromPrompts | None
    upload: FakeUploadImageToLibraryTool
    genai_client: FakeGenaiClientFactory
    httpx_get: FakeHttpxGet
    sleep: FakeAsyncSleep
    events: EventLog
    logs: LogCapture | None
    settings: Any
    assign_territories: CallSpy | None = None
    skipped: list[str] = field(default_factory=list)

    def checkpoint(self, task_id: str, ad_id: Any, step: str) -> Any:
        return self.redis.checkpoint(task_id, ad_id, step)


@contextmanager
def patched_diversity_pipeline(
    *,
    adset_context: Mapping[str, Any] | None = None,
    ad_ids: Iterable[Any] | None = None,
    redis: FakeRedis | None = None,
    run_agent: FakeRunAgent | None = None,
    factories: FakeAgentFactories | None = None,
    get_adset_context: FakeGetAdsetContext | None = None,
    get_template_context: FakeGetTemplateContext | None = None,
    get_a_template_definition: FakeGetATemplateDefinition | None = None,
    get_ctas: FakeGetCtas | None = None,
    save_ads: FakeSaveAds | None = None,
    delete_variants: FakeDeleteVariants | None = None,
    post_to_abyssale: FakePostToAbyssaleAndWait | None = None,
    generate_images: FakeGenerateImagesFromPrompts | None = None,
    real_image_generator: bool = False,
    upload: FakeUploadImageToLibraryTool | None = None,
    genai_client: FakeGenaiClientFactory | None = None,
    httpx_get: FakeHttpxGet | None = None,
    sleep: FakeAsyncSleep | None = None,
    diversity_flag: bool | None = True,
    use_mock_sinergia: bool = True,
    territory_engine: bool = False,
    debug: bool = False,
    max_concurrent_ads: int | None = None,
    abyssale_api_key: str | None = None,
    spy_assign_territories: bool = True,
    block_network: bool = True,
    capture_logs: bool = True,
    extra_patches: Iterable[tuple[Any, str, Any]] = (),
) -> Iterator[DiversityHarness]:
    """Patch `_run_phase1`'s collaborators and settings; restore in `finally`.

    Patched:
      services.job_runner_service: `_run_agent` (FakeRunAgent), `_redis`
          (→ FakeRedis), `_load` / `_store` (same JSON semantics on the fake);
          the tool/factory names below only if they are module-level names there
      agents.<x>_agent: every `make_<x>_agent` of FACTORY_TARGETS
      agents.tools.mock_sinergia and agents.tools.campaign_tools: the
          SINERGIA_TOOL_NAMES tools and `upload_image_to_library`
      agents.nano_banana_agent: `upload_image_to_library_tool` and, unless
          `real_image_generator=True`, `generate_images_from_prompts`
      agents.tools.abyssale_tools: `post_to_abyssale_and_wait`
      google.genai: `Client`;  httpx: `get`;  asyncio: `sleep`
      services.territory_assignment: `assign_territories` wrapped in a CallSpy
          (real behaviour) when `spy_assign_territories=True`
      settings: USE_MOCK_SINERGIA, USE_TERRITORY_ENGINE, DEBUG and, when not
          None, USE_ADSET_CREATIVE_DIVERSITY (`diversity_flag`),
          ADS_MAX_CONCURRENT_ADS, ABYSSALE_API_KEY

    `adset_context` / `ad_ids` build the default FakeGetAdsetContext
    (`make_adset_context(ad_ids)` when only `ad_ids` is given).
    `extra_patches` items are `(module_or_dotted_path_or_object, attr, value)`.
    """
    from core.config import settings

    if get_adset_context is None:
        if adset_context is None:
            adset_context = make_adset_context(ad_ids or ())
        get_adset_context = FakeGetAdsetContext(adset_context)

    events = EventLog()
    harness = DiversityHarness(
        redis=redis if redis is not None else FakeRedis(),
        run_agent=run_agent or FakeRunAgent(),
        factories=factories or FakeAgentFactories(),
        get_adset_context=get_adset_context,
        get_template_context=get_template_context or FakeGetTemplateContext(),
        get_a_template_definition=get_a_template_definition or FakeGetATemplateDefinition(),
        get_ctas=get_ctas or FakeGetCtas(),
        save_ads=save_ads or FakeSaveAds(),
        delete_variants=delete_variants or FakeDeleteVariants(),
        post_to_abyssale=post_to_abyssale or FakePostToAbyssaleAndWait(),
        generate_images=None if real_image_generator else (
            generate_images or FakeGenerateImagesFromPrompts()
        ),
        upload=upload or FakeUploadImageToLibraryTool(),
        genai_client=genai_client or FakeGenaiClientFactory(),
        httpx_get=httpx_get or FakeHttpxGet(),
        sleep=sleep or FakeAsyncSleep(),
        events=events,
        logs=LogCapture() if capture_logs else None,
        settings=settings,
    )
    for fake in (
        harness.get_adset_context, harness.get_template_context,
        harness.get_a_template_definition, harness.get_ctas, harness.save_ads,
        harness.delete_variants, harness.post_to_abyssale, harness.upload,
        harness.generate_images,
    ):
        if fake is not None:
            fake.bind_events(events)

    tools: dict[str, Any] = {
        "get_adset_context": harness.get_adset_context,
        "get_template_context": harness.get_template_context,
        "get_a_template_definition": harness.get_a_template_definition,
        "get_ctas": harness.get_ctas,
        "save_ads": harness.save_ads,
        "delete_variants": harness.delete_variants,
    }

    patcher = AttrPatcher()
    settings_patcher = SettingsPatcher(settings)

    with ExitStack() as stack:
        try:
            if block_network:
                stack.enter_context(network_guard())
            if harness.logs is not None:
                stack.enter_context(harness.logs)

            # settings
            settings_patcher.set("USE_MOCK_SINERGIA", use_mock_sinergia)
            settings_patcher.set("USE_TERRITORY_ENGINE", territory_engine)
            settings_patcher.set("DEBUG", debug)
            if diversity_flag is not None:
                settings_patcher.set("USE_ADSET_CREATIVE_DIVERSITY", diversity_flag)
            if max_concurrent_ads is not None:
                settings_patcher.set("ADS_MAX_CONCURRENT_ADS", max_concurrent_ads)
            settings_patcher.set("ABYSSALE_API_KEY", abyssale_api_key)

            # services.job_runner_service
            jrs = importlib.import_module(_JOB_RUNNER)
            fake_redis = harness.redis

            def _fake_store(key: str, value: Any, ex: int = 86400 * 7) -> None:
                fake_redis.set(key, json.dumps(value), ex=ex)

            def _fake_load(key: str) -> Any:
                raw = fake_redis.get(key)
                return json.loads(raw) if raw else None

            patcher.set(jrs, "_redis", lambda: fake_redis)
            patcher.set(jrs, "_store", _fake_store)
            patcher.set(jrs, "_load", _fake_load)
            patcher.set(jrs, "_run_agent", harness.run_agent)
            for name, fake in tools.items():
                patcher.set_if_present(jrs, name, fake)
            for name, fake in (
                ("post_to_abyssale_and_wait", harness.post_to_abyssale),
                ("generate_images_from_prompts", harness.generate_images),
            ):
                if fake is not None:
                    patcher.set_if_present(jrs, name, fake)

            # agent factories
            for agent_name, (dotted, attr) in FACTORY_TARGETS.items():
                factory = harness.factories.factories.get(agent_name)
                if factory is None:
                    continue
                patcher.set_if_present(jrs, attr, factory)
                module = _import_optional(dotted)
                if module is None:
                    harness.skipped.append(dotted)
                    continue
                patcher.set(module, attr, factory)

            # Sinergia tools (mock and real modules: lazy imports read them at call time)
            for dotted in (_MOCK_SINERGIA, _CAMPAIGN_TOOLS):
                module = _import_optional(dotted)
                if module is None:
                    harness.skipped.append(dotted)
                    continue
                for name, fake in tools.items():
                    patcher.set(module, name, fake)
                patcher.set(module, "upload_image_to_library", harness.upload)

            # Image_Generator
            nano = _import_optional(_NANO_BANANA)
            if nano is None:
                harness.skipped.append(_NANO_BANANA)
            else:
                patcher.set(nano, "upload_image_to_library_tool", harness.upload)
                if harness.generate_images is not None:
                    patcher.set(nano, "generate_images_from_prompts", harness.generate_images)

            # Abyssale
            abyssale = _import_optional(_ABYSSALE_TOOLS)
            if abyssale is None:
                harness.skipped.append(_ABYSSALE_TOOLS)
            else:
                patcher.set(abyssale, "post_to_abyssale_and_wait", harness.post_to_abyssale)

            # Gemini client, httpx downloads, asyncio.sleep
            genai = _import_optional(_GENAI)
            if genai is None:
                harness.skipped.append(_GENAI)
            else:
                patcher.set(genai, "Client", harness.genai_client)
            patcher.set(httpx, "get", harness.httpx_get)
            patcher.set(asyncio, "sleep", harness.sleep)

            # assign_territories spy (real behaviour, call count for resume checks)
            if spy_assign_territories:
                territory = importlib.import_module(_TERRITORY)
                spy = CallSpy(territory.assign_territories)
                patcher.set(territory, "assign_territories", spy)
                harness.assign_territories = spy

            for target, name, value in extra_patches:
                obj = importlib.import_module(target) if isinstance(target, str) else target
                patcher.set(obj, name, value)

            yield harness
        finally:
            patcher.undo()
            settings_patcher.undo()


def run_phase1(
    *,
    task: Any = None,
    task_id: str = DEFAULT_TASK_ID,
    id_adset: int = 173,
    n_variants: int = 2,
    project_id: str | None = DEFAULT_PROJECT_ID,
    id_ad: int | None = None,
    custom_prompt: str | None = None,
    add_variant: bool = True,
    id_variant: list[int] | None = None,
) -> dict[str, Any]:
    """Run `job_runner_service._run_phase1` to completion (call inside
    `patched_diversity_pipeline`)."""
    jrs = importlib.import_module(_JOB_RUNNER)
    return asyncio.run(
        jrs._run_phase1(
            task, task_id, id_adset, n_variants, project_id,
            id_ad=id_ad, custom_prompt=custom_prompt,
            add_variant=add_variant, id_variant=id_variant,
        )
    )
