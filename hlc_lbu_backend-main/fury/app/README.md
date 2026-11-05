# Fury API - Ad Text Generation Service

AI-powered ad text generation service built with FastAPI, LangChain, and LangGraph.

## Project Structure

```
app/
├── api/                    # API routes
│   ├── v2/                 # API version 2
│   │   ├── endpoints/      # Endpoint modules
│   │   │   ├── ad_generation.py
│   │   │   ├── variants.py
│   │   │   └── health.py
│   │   └── router.py       # Main v2 router
│   └── dependencies.py     # FastAPI dependencies
├── agents/                 # ADK agents (7-step pipeline)
│   ├── root_orchestrator.py
│   ├── data_collector_agent.py
│   ├── estratega_agent.py
│   ├── copywriter_agent.py
│   ├── image_prompter_agent.py
│   ├── validador_agent.py
│   ├── nano_banana_agent.py
│   ├── template_mapper_agent.py
│   ├── guards/             # Per-agent safeguards
│   └── tools/
│       ├── campaign_tools.py   # Real Sinergia calls
│       └── mock_sinergia.py    # Mock data for local dev
├── core/                   # Core functionality
│   ├── config.py           # Configuration settings
│   ├── logging.py          # Logging setup
│   ├── adk_config.py       # ADK/Gemini runner setup
│   └── exceptions.py       # Custom exceptions
├── schemas/                # Pydantic models
├── services/               # Business logic
│   ├── celery_app.py
│   └── job_runner_service.py
├── utils/                  # Utility modules
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── env.example             # Environment variables template
├── README.md               # This file
└── DEVELOPMENT.md          # Local development guide
```

## Features

- **Modular Architecture**: Clean separation of concerns with core, services, utils, and API layers
- **Type Safety**: Full Pydantic validation for requests and responses
- **AI Integration**: 
  - Google Gemini (ADK) for the 7-agent ad generation pipeline
  - OpenAI for text generation
  - Qdrant for vector stores
  - PostgreSQL for chat memory
  - Langfuse for prompt management and observability
- **API Versioning**: Support for multiple API versions
- **Error Handling**: Custom exceptions with proper HTTP status codes
- **Logging**: Structured logging with Loguru
- **Dependency Injection**: FastAPI dependencies for clean service management

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Run the application**:
   ```bash
   # Development
   python main.py
   
   # Production
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

> **Local development guide (mock Sinergia, no Celery/Redis):** see [DEVELOPMENT.md](DEVELOPMENT.md)

## Environment Variables

See `env.example` for all available configuration options.

Key variables:
- `STRAPI_URL`, `STRAPI_TOKEN`: Strapi CMS connection
- `QDRANT_URL`: Qdrant vector store
- `DATABASE_*`: PostgreSQL database connection
- `OPENAI_API_KEY`: OpenAI API credentials
- `LANGFUSE_*`: Langfuse prompt management
- `GOOGLE_API_KEY`: Google Gemini / ADK
- `SINERGIA_URL`, `SINERGIA_SERVICE_API_KEY`: Sinergia service connection
- `USE_MOCK_SINERGIA`: Set `true` to bypass Sinergia locally
- `REDIS_HOST`, `REDIS_PORT`: Redis for Celery

## API Endpoints

### Health Check
```bash
GET /api/v2/health
```

### Generate Ad Variants (Celery)
```bash
POST /api/v2/variants
```

**Request Body**:
```json
{
  "id_adset": 295,
  "n_variants": 3,
  "template_id": null
}
```

**Response**:
```json
{
  "ok": 1,
  "data": {
    "variant_job_id": "uuid",
    "status": "RUNNING",
    "poll_url": "/api/v2/jobs/uuid"
  }
}
```

### Generate Ad Variants — Inline/Dev (no Celery)
```bash
POST /api/v2/variants/run-local   # Only available when DEBUG=true
```

Returns the full pipeline result directly (no polling needed).

### Poll Job Status
```bash
GET /api/v2/jobs/{task_id}
```

### Generate Ad Text (legacy)
```bash
POST /api/v2/ad/media/elements/generate_text
```

### Vertex AI Agent Engine Tools (Shadow Testing)
These endpoints are exposed exclusively for Google Cloud Agent Engine. They use OIDC token verification to securely fetch context from Sinergia.
```bash
GET /api/v2/agent-tools/adset_context/{id_adset}
GET /api/v2/agent-tools/brand_context/{brand_id}
GET /api/v2/agent-tools/template_context/{project_id}
GET /api/v2/agent-tools/ctas
# ... see Swagger docs for complete list
```

## Agent Engine Deployment (Shadow Migration)

The pipeline is actively migrating from an **embedded** model (running agents locally in Celery) to Google Cloud's **Vertex AI Agent Engine**.

During this transition, we run a "Shadow Migration":
1. When an ad generation job starts, Celery processes the pipeline locally as normal.
2. It simultaneously triggers the remote Agent Engine in parallel using `run_shadow_pipeline`.
3. The remote Agent Engine connects back to the backend via the `/agent-tools` endpoints to gather context.

To deploy the shadow agent graph to GCP:
```bash
# Deploys the mocked tool version of the agent to your GCP project
python deploy_agent_engine.py
```
*Note: Update the `tool_base_url` in the script to match your live backend URL before deploying.*

## Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Adding New Agents

1. Create agent in `agents/`
2. Register it in `agents/root_orchestrator.py`
3. Add guard in `agents/guards/` if needed

### Adding New Endpoints

1. Create endpoint module in `api/v2/endpoints/`
2. Add router to `api/v2/router.py`
3. Add schemas in `schemas/`
4. Implement business logic in `services/`

### Custom Exceptions

Define in `core/exceptions.py`:
```python
class MyException(FuryException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="MY_ERROR",
            status_code=400
        )
```

## Architecture Principles

- **Separation of Concerns**: Clear boundaries between layers
- **Dependency Injection**: Services injected via FastAPI
- **Type Safety**: Pydantic models for all data
- **Error Handling**: Custom exceptions with proper codes
- **Logging**: Structured logging throughout
- **Configuration**: Centralized in `core/config.py`


## Docker commands

```bash
docker build -t fury-api -f app/Dockerfile app
docker run --rm -p 8000:8000 --env-file app/.env fury-api
```

## License

Proprietary - HiLuca
