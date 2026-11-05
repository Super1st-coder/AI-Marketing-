#!/bin/bash
echo "Starting Fury API + Celery worker..."

export PYTHONPATH=/app

mkdir -p logs/fury

celery -A services.celery_app worker \
    --loglevel INFO \
    --uid 0 \
    &

echo "Esperando a que los workers de Celery registren las tareas..."
# Intenta hacer un ping al worker. Si falla, espera 2 segundos y reintenta.
until celery -A services.celery_app inspect ping &>/dev/null; do
  echo "Celery aún no está listo. Reintentando en 2 segundos..."
  sleep 2
done

echo "¡Celery está listo!"
echo "Iniciando la API..."

uvicorn main:app --host 0.0.0.0 --port 8000 &

while true; do sleep 1000; done
