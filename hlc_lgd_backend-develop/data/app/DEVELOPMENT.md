# Data Backend Service — Local Development Guide

Guide to quickly iterate on your new data backend service.

## Table of Contents

- [Requirements](#requirements)
- [Local Mode (Development)](#local-mode-development)
- [Base Architecture](#base-architecture)
- [Project Structure](#project-structure)
- [Debugging Tips](#debugging-tips)

---

## Requirements

To run this service locally you will need:
- **Python 3.11+**
- **PostgreSQL** (running locally or via Docker)
- **Redis** (for asynchronous tasks with Celery)

---

## Local Mode (Development)

### 1. Environment Variables (`.env`)

Copy the example file to create your local configuration:
```bash
cp env.example .env
```

Configure your PostgreSQL credentials and make sure `DEBUG=True` is set.

### 2. Start the API

With your virtual environment activated, install dependencies and run the development server:

```bash
pip install -r requirements.txt
python main.py
```

The interactive API documentation will be available at:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### 3. Start Celery (Optional)

If you add asynchronous tasks in the future, start Redis and the Celery worker in a second terminal:

```bash
# MacOS
brew services start redis

# Celery Worker (development mode)
PYTHONPATH=. celery -A services.celery_app worker --loglevel INFO --pool solo
```

---

## Base Architecture

This clean framework comes with the following pre-configured components:
- **FastAPI**: Modern, asynchronous, and auto-documented routing.
- **PostgreSQL (`utils/postgres_client.py`)**: Standard client based on `psycopg` to interact with the database cleanly.
- **Celery (`services/celery_app.py`)**: Ready-to-use configuration for background jobs using Redis as a broker.
- **Internal Authentication (`core/auth.py`)**: Ready-to-use middleware (`verify_internal_api_key`) to protect endpoints so that only internal microservices can call them by passing the `X-Internal-API-Key` header.

---

## Project Structure

```text
app/
├── api/
│   └── v2/
│       ├── endpoints/
│       │   ├── health.py        # Basic healthcheck
│       │   └── sample.py        # Example endpoint
│       └── router.py            # Main router registry
├── core/
│   ├── auth.py                  # Security and auth utilities
│   ├── config.py                # Global Pydantic Settings
│   ├── exceptions.py            # Custom exception handling
│   └── logging.py               # Standard logger
├── schemas/
│   ├── common.py                # Standard responses (SuccessResponse, ErrorResponse)
│   └── sample_schemas.py        # Example Pydantic validation
├── services/
│   ├── celery_app.py            # Celery application instance
│   └── sample_service.py        # Example Business Logic
└── utils/
    └── postgres_client.py       # PostgreSQL connection wrapper
```

---

## Debugging Tips

```bash
# Check if Redis is alive
redis-cli ping   # → PONG

# Clear Redis queues if tasks get stuck
redis-cli FLUSHDB

# Hot-reload
# When `DEBUG=True` is set in your .env, saving any changes to 
# `.py` files will automatically restart the FastAPI server.
```
