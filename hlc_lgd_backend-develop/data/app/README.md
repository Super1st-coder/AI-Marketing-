# Data Backend Service

A high-performance data processing backend service built with FastAPI, PostgreSQL, and Celery.

## Project Structure

```
app/
├── api/                    # API routes
│   ├── v2/                 # API version 2
│   │   ├── endpoints/      # Endpoint modules
│   │   │   ├── health.py   # Healthcheck endpoint
│   │   │   └── sample.py   # Example endpoint
│   │   └── router.py       # Main v2 router
│   └── dependencies.py     # FastAPI dependencies
├── core/                   # Core functionality
│   ├── auth.py             # Security and authentication (Internal API keys)
│   ├── config.py           # Configuration settings
│   ├── exceptions.py       # Custom exceptions
│   └── logging.py          # Logging setup
├── schemas/                # Pydantic models for validation
│   ├── common.py           # Standard response schemas
│   └── sample_schemas.py   # Example schemas
├── services/               # Business logic and background tasks
│   ├── celery_app.py       # Celery configuration
│   └── sample_service.py   # Example business logic
├── utils/                  # Utility modules
│   └── postgres_client.py  # Clean PostgreSQL client wrapper
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── env.example             # Environment variables template
├── README.md               # This file
└── DEVELOPMENT.md          # Local development guide
```

## Features

- **Modular Architecture**: Clean separation of concerns with core, services, utils, and API layers.
- **Type Safety**: Full Pydantic validation for requests and responses.
- **Asynchronous Tasks**: Pre-configured Celery integration backed by Redis for heavy background processing.
- **PostgreSQL Ready**: Standard database connection utilities built on `psycopg`.
- **API Versioning**: Scalable support for multiple API versions.
- **Error Handling**: Custom exceptions with proper HTTP status codes and unified response formats.
- **Service Security**: Built-in `X-Internal-API-Key` authentication middleware for securing service-to-service communication.
- **Logging**: Structured logging with Loguru.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your PostgreSQL/Redis credentials
   ```

3. **Run the application**:
   ```bash
   # Development
   python main.py
   
   # Production
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

> **Local development guide:** see [DEVELOPMENT.md](DEVELOPMENT.md) for detailed instructions on running locally with Celery and Redis.

## Environment Variables

See `env.example` for all available configuration options.

Key variables:
- `DATABASE_*`: PostgreSQL database connection settings.
- `REDIS_HOST`, `REDIS_PORT`: Redis connection for Celery broker.
- `FURY_INTERNAL_API_KEY`: Shared secret required to hit protected internal endpoints.
- `DEBUG`: Enables hot-reloading and detailed logging.

## API Endpoints

### Health Check
```bash
GET /api/v2/health
```

### Sample Protected Endpoint
```bash
GET /api/v2/sample
```

## Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Adding New Endpoints

1. Create a new endpoint module in `api/v2/endpoints/`.
2. Add the router to `api/v2/router.py`.
3. Add request/response schemas in `schemas/`.
4. Implement the underlying business logic in `services/`.

### Custom Exceptions

Define new application-level errors in `core/exceptions.py`:
```python
class MyCustomException(FuryException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="MY_ERROR",
            status_code=400
        )
```

## Docker deployment

To build and run the service via Docker:
```bash
docker build -t data-backend-api -f app/Dockerfile app
docker run --rm -p 8000:8000 --env-file app/.env data-backend-api
```

## License

Proprietary - HiLuca
