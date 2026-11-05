#!/bin/bash
echo "Starting Fury API + Celery worker..."

export PYTHONPATH=/app

mkdir -p logs/fury

celery -A services.celery_app worker \
    --loglevel INFO \
    --uid 0 \
    &

uvicorn main:app --host 0.0.0.0 --port 8000 &

while true; do sleep 1000; done
