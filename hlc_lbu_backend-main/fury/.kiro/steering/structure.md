---
inclusion: always
---

# Fury — Project Structure & Where Things Go

Fury is HiLuca's ad-generation service, living at `docker-deploy/fury/`. All code is under `fury/app/`, which is the import root. Imports are absolute from there (`from services.x import y`). Stack and coding conventions are in `tech.md`. This file covers where code lives and how the pieces connect.

## Directory Map (`fury/app/`)

| Path | Responsibility |
|---|---|
| `main.py` | App factory, CORS, global exception handlers, mounts the v2 router at `settings.API_V2_PREFIX` (`/api/v2`). |
| `api/v2/router.py` | Registers every endpoint router with its prefix and tags. |
| `api/v2/endpoints/` | One router module per resource. Keep them thin. |
| `api/dependencies.py` | FastAPI DI providers. |
| `agents/` | One ADK agent per `<name>_agent.py`, exposed as `make_<name>_agent()`. |
| `agents/guards/` | Model callbacks (`safety_guard`, `copywriter_guard`, `data_collector_guard`), re-exported from `agents/guards/__init__.py`. |
| `agents/tools/` | Tool functions. `campaign_tools.py` is the only Sinergia client; `mock_sinergia.py` mirrors it. Also `abyssale_tools.py`, `creative_tools.py`, `validation_tools.py`. |
| `services/` | Pipeline orchestration (Celery tasks), validators, and deterministic engines. |
| `schemas/` | Pydantic models, one file per domain (`pipeline_schemas`, `persona_schemas`, `territory_schemas`, `llm_schemas`, `ad_generation`, `common`). |
| `core/` | Settings, auth, ADK/Langfuse config, exceptions, validation errors, logging, Redis session service. |
| `helpers/agent.py` | `run_agent()`, used to execute any agent (imported as `_run_agent` in job runners). |
| `utils/` | Legacy clients (Postgres, Qdrant, Strapi, Langfuse). Don't extend them for pipeline work. |
| `tests/` | `test_<module>.py` for deterministic logic. They run under pytest or as `python -m tests.<name>`. |
| `env/`, `logs/` | Local virtualenv and runtime logs. Never read, edit, or search them. |

Runtime: `Dockerfile` plus `supervisord.conf` run uvicorn (`main:app`, port 8000) and Celery workers (`services.celery_app`) in one container.

## Request → Pipeline Flow

1. An endpoint in `api/v2/endpoints/` validates the request with a `schemas/` model, authenticates, and calls `<task>.apply_async(...)`.
2. A Celery task in `services/*_job_runner_service.py` (sync wrapper) runs an `async def _run_<pipeline>()` coroutine.
3. The coroutine imports agent factories lazily inside the function, then picks `campaign_tools` or `mock_sinergia` based on `settings.USE_MOCK_SINERGIA`. It runs each step through `_run_agent(...)` with a `services/*_validators.py` validator and checkpoints results to Redis (`_cp_key` / `_store` / `_load`).
4. Results go back to Sinergia via `campaign_tools`. Abyssale renders return through `webhooks.py`, and `finalize_job` / `mark_job_failed` close the job.
5. Clients poll `GET /api/v2/jobs/{task_id}`.

Orchestration is code-driven. The order of steps lives in the job runner, not in an LLM orchestrator.

## Pipelines

| Pipeline | Endpoint (`/api/v2/...`) | Celery task(s) | Agents used |
|---|---|---|---|
| Ad variants | `POST /variants`, `/variants/run-local` | `job_runner_service.run_pipeline_phase1` (+ `trigger_ai_expansion`, `finalize_job`, `mark_job_failed`, `run_shadow_pipeline`) | data_collector, estratega (or estratega_adset when Phase-A territories are on), copywriter, image_prompter, validador, nano_banana, template_mapper |
| Persona main image | `POST /persona-images`, `/run-local` | `persona_job_runner_service.run_persona_pipeline` | persona_data_collector, persona_prompter, persona_auditor, nano_banana (`generate_images_from_prompts`) |
| Persona edit | `POST /persona-images/edit/main-image`, `/edit/variant` | `run_edit_persona_main_image_pipeline` | persona_data_collector, edit_prompter |
| Persona variations | `POST /persona-images/main-image/variant/generate` | `run_generate_persona_image_variations_pipeline` | persona_data_collector, persona_variants_prompter |

Other routers: `health`, `jobs` (polling), `webhooks` (Abyssale and AI expansion), `agent_tools` (read-only Sinergia context for Agent Engine, OIDC), `llm` (hypothesis extraction), `ad_generation` (legacy).

## Where to Put New Code

- New endpoint: add a module in `api/v2/endpoints/` with `router = APIRouter()`, then register it in `api/v2/router.py` with a prefix and tag. A module that isn't registered isn't served.
- New agent: create `agents/<name>_agent.py` with `make_<name>_agent()`. Import it lazily inside the job runner coroutine that uses it.
- New pipeline step: put it in the relevant `_run_*` coroutine. Give it its own checkpoint key and validator.
- New Celery task module: add it to `include=[...]` in `services/celery_app.py`.
- New Sinergia call: add it to `agents/tools/campaign_tools.py`, with a matching function of the same signature in `agents/tools/mock_sinergia.py`.
- New structured agent output: write a Pydantic model in `schemas/` and a `validate_<agent>_response` in `services/ads_validators.py` (ads) or `services/persona_validators.py` (persona).
- Deterministic business rules (limits, assignment, compositing): write a standalone module in `services/` with a matching `tests/test_<module>.py`.
- New setting: put it in `core/config.py`, documented in `env.example`. New errors subclass `FuryException` in `core/exceptions.py`.

## Legacy / Unwired Code (don't build on it)

- `agents/root_orchestrator.py` imports module-level agent singletons that no longer exist (only `make_*` factories do), and nothing imports it. Don't register new agents there or import it. Pipelines are orchestrated in `services/*_job_runner_service.py`.
- `api/v2/endpoints/poc.py` and `services/poc_service.py` are not mounted in `router.py`.
- `utils/*_client.py`, `ad_generation` endpoint/service, LangChain/LangGraph, Qdrant, and Postgres paths are legacy.
- `agents/tools/cloud_mock_tools.py` and `deploy_agent_engine.py` are for Agent Engine deployment and shadow testing, not the Celery pipeline.

## Related Docs

- `fury/PHASE_A_TERRITORY_ROLLOUT.md`: how to enable and validate the flagged Phase-A territory engine (`territory_assignment.py`, `estratega_adset_agent.py`, `territory_schemas.py`).
- `app/README.md`, `app/DEVELOPMENT.md`: setup and local development.
