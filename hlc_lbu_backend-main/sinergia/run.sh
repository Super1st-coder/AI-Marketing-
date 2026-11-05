#!/bin/bash
echo "Starting Sinergia  -\-/- ..."

export CONFIG_TYPE=dev

echo "Inicializando base de datos (creación de tablas)..."
python manage.py db_init || echo "Warning: db_init failed, continuing..."

nohup celery -A make_celery worker --loglevel INFO -n "worker_${RANDOM}@%h" --uid 0 &

echo "Esperando a que los workers de Celery registren las tareas..."
# Intenta hacer un ping al worker. Si falla, espera 2 segundos y reintenta.
until celery -A make_celery inspect ping &>/dev/null; do
  echo "Celery aún no está listo. Reintentando en 2 segundos..."
  sleep 2
done

echo "¡Celery está listo!"
echo "Iniciando la API..."

gunicorn -b 0.0.0.0:60000 -w 5 -k gevent --keep-alive 10 --timeout 300 --access-logfile - --error-logfile - manage:app