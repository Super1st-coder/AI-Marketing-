---
inclusion: always
---

# Fury — Tech Stack & Engineering Conventions

Fury is HiLuca's AI ad-generation service: a FastAPI API plus Celery workers that run a multi-agent Google ADK pipeline (ad variants, persona images). Sinergia is the system of record; Fury reads context from it and writes results back.

## Stack

- Python 3.11, FastAPI + Uvicorn, Pydantic v2 / pydantic-settings.
- Google ADK (`google-adk`, `google-genai`) for agents; models routed through LiteLLM (`LiteLlm`).
- Celery + Redis (broker, result backend, ADK sessions, step checkpoints, Sinergia cache).
- Langfuse for prompt management (`label="latest"`) and tracing (`@observe`).
- Loguru logging, httpx for outbound HTTP.
- Image providers: Gemini (Nano Banana), fal.ai, Abyssale templates; optional `rembg`/Pillow compositing.
- Legacy pieces still present: LangChain/LangGraph, OpenAI, Qdrant, PostgreSQL (`ad_generation`, `utils/*_client.py`). Do not extend these for new pipeline work.

## Layout (all code lives under `fury/app/`, which is the import root)

- `main.py` — app factory, CORS, global exception handlers, mounts v2 router.
- `api/v2/endpoints/` — thin routers; registered in `api/v2/router.py`. `api/dependencies.py` holds DI providers.
- `agents/` — one ADK agent per file, exposed as a `make_<name>_agent()` factory. `agents/guards/` = model callbacks; `agents/tools/` = tool functions.
- `agents/tools/campaign_tools.py` — the ONLY place Sinergia is called. `mock_sinergia.py` mirrors it with adset-295 data.
- `services/` — business logic, Celery tasks (`job_runner_service.py`, `persona_job_runner_service.py`), response validators (`ads_validators.py`, `persona_validators.py`), deterministic engines (`territory_assignment.py`, `text_limits.py`).
- `schemas/` — Pydantic request/response and pipeline models.
- `core/` — `config.py` (settings), `auth.py`, `sinergia_auth.py`, `adk_config.py`, `exceptions.py`, `validation.py`, `logging.py`.
- `helpers/agent.py` — `run_agent()`, the standard way to execute an agent.
- `tests/` — pytest-style tests that also run as plain modules.

Imports are absolute from the app root (`from core.config import settings`, `from services.x import y`), never `from app.…` or `fury.app.…`. Run commands with `PYTHONPATH=.` from `fury/app`.

## Architecture Rules

- Endpoints stay thin: validate with a schema, authenticate, enqueue a Celery task (`.apply_async`) or call a service. Long work never runs in the request.
- Async job pattern: `POST` returns `201` with `{"ok": 1, "data": {"<x>_job_id", "status": "RUNNING", "poll_url": "/api/v2/jobs/{id}"}}`; clients poll `GET /jobs/{task_id}`.
- `/run-local` endpoints run the pipeline inline for dev and MUST return 404 unless `settings.DEBUG` is true.
- Celery tasks are sync wrappers that run the async pipeline on a dedicated event loop (`loop.run_until_complete`), not `asyncio.run()`. Respect `task_soft_time_limit`, `acks_late`, and `max_retries`; new tasks must be listed in `celery_app.include`.
- Pipeline steps checkpoint to Redis via `_store` / `_load` with `_cp_key(task_id, …, step)` so retries resume instead of recomputing. Keep this for any new step.
- Context is assembled once by code and injected into the agent message ("assemble-once"). Downstream agents get `tools=[]`; only data-collector agents call Sinergia tools.
- Prefer deterministic code over LLM judgment for structural decisions (e.g. territory assignment). The LLM writes content within constraints chosen by code.
- New behavior that changes pipeline output goes behind a `USE_*` flag in `core/config.py`, default `False`, with the legacy path left byte-for-byte unchanged.
- Respect `settings.USE_MOCK_SINERGIA`: anything new in `campaign_tools.py` needs a matching mock in `mock_sinergia.py`.

## Agent Conventions

- Each agent file defines a `_FALLBACK_INSTRUCTION` and a `make_<name>_agent(custom_prompt: str | None = None)` lazy factory (no module-level singletons).
- Load instruction + model with `get_agent_config_from_langfuse("fury.<agent_name>", _FALLBACK_INSTRUCTION, fallback_model=…, cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS)`. Langfuse prompt names use the `fury.` prefix; the model lives in the prompt's `config.model`.
- Model strings MUST keep the provider prefix (`gemini/gemini-2.5-pro`). A bare `gemini-2.5-pro` routes to Vertex and fails with `DefaultCredentialsError`.
- Append `custom_prompt` to the instruction; it may refocus content but never override hard constraints.
- Always attach `safety_guard_before_model` / `safety_guard_after_model` from `agents.guards`.
- Agents that return structured output must be told to return ONLY JSON, and paired with a `validate_<agent>_response(response: str) -> ValidationResult` in `services/*_validators.py`.
- Run agents via `helpers.agent.run_agent(agent, user_id, message_text, validator=…)`. It may return raw text OR parsed `ValidationResult.data`; callers must handle both (see `_parse_json_response`).
- Validation failures raise `core.validation.AgentValidationError` (keep it picklable for Celery).
- Prompts must ground claims in real product/buyer data and comply with Meta ad policy.
- Pipelines are orchestrated in code by `services/*_job_runner_service.py`. Import new agents lazily inside the `_run_*` coroutine that uses them. Don't register agents in `agents/root_orchestrator.py` (legacy, unwired, see `structure.md`).

## Configuration

- All settings live in `core/config.py` (`settings` singleton, pydantic-settings, env-driven). Never read `os.environ` directly in feature code.
- Add new vars to `core/config.py` with safe defaults and document them in `env.example`.
- Never commit or log secrets; `.env`, credentials, and API keys stay out of code and logs.

## Security

- Sinergia → Fury endpoints: `Depends(verify_internal_api_key)` (`X-Internal-API-Key`, constant-time compare).
- Agent Engine tool endpoints (`/agent-tools`): `Depends(verify_oidc_token)`.
- Abyssale / AI-expansion webhooks: secret path parameter checked against `ABYSSALE_WEBHOOK_SECRET`.
- Fury → Sinergia calls use `sinergia_auth.get_token()` and the `X-Service-API-Key` header.
- Every new endpoint must use one of these mechanisms; flag any unauthenticated route.
- Strip signed URLs from payloads before logging or storing them (`_strip_signed_urls`).

## Errors & Responses

- Raise `FuryException` subclasses from `core/exceptions.py` (`code`, `status_code`, `details`); global handlers render `{"ok": 0, "message": {"code", "text"}, "details"}`.
- Success envelopes use `{"ok": 1, "data": …}`.
- Detect provider rate limits (429 / `RESOURCE_EXHAUSTED`) and retry with backoff instead of failing the job.

## Code Style

- Module docstring at the top of every file explaining purpose and, for pipeline code, its place in the architecture.
- Type hints everywhere, modern syntax (`str | None`, `list[dict]`, `dict[str, Any]`).
- Logging: `logger = get_logger(__name__)` from `core.logging`; f-strings with a bracketed context prefix, e.g. `logger.info(f"[{task_id}] → strategy ad={ad_id}")`, `"[Langfuse] …"`, `"[ADK] …"`.
- Private helpers are `_prefixed`. Constants are `UPPER_SNAKE`.
- Comments explain WHY, citing the ticket when relevant (e.g. `# HL-2630: …`). Keep these when editing.
- Domain terms are often Spanish (`estratega`, `validador`, `territorio_prohibido`, `hablarle_de`); keep existing names rather than translating.
- Pin new dependencies to exact versions in `requirements.txt`.

## Commands (from `fury/app`)

```bash
python main.py                                   # API with hot reload when DEBUG=true → :8000/docs
PYTHONPATH=. celery -A services.celery_app worker --loglevel INFO --pool solo   # debuggable worker
PYTHONPATH=. python -m tests.test_territory_assignment   # run a test module (no pytest needed)
PYTHONPATH=. pytest tests/                       # pytest is not in requirements.txt; install it locally first
docker build -t fury-api -f app/Dockerfile app   # from fury/; prod runs supervisord (uvicorn + 3 Celery workers)
```

Fastest local loop: `DEBUG=true`, `USE_MOCK_SINERGIA=true`, `GOOGLE_API_KEY` set, then `POST /api/v2/variants/run-local` with `{"id_adset": 295, "n_variants": 1}`. No Redis or Celery needed.

## Testing

- Test deterministic logic (validators, territory assignment, text limits, parsers) without network or LLM calls, using `mock_sinergia` fixtures (`copy.deepcopy(_MOCK_ADSET)`).
- Write tests as plain `test_*` functions with `assert` so they work under pytest and `python -m`.
- The dev host can be geo-blocked from the Gemini API; live LLM validation happens in dev/QAS. Say so explicitly when an LLM path could not be verified locally.
