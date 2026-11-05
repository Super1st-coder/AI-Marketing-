# Fury — Local Development Guide

Guía para iterar rápido en Fury sin necesitar Sinergia, Celery ni Redis.

## Índice

- [Modo ultrarrápido (sin Celery, sin Redis, sin Sinergia)](#modo-ultrarrápido)
- [Modo sin Sinergia (con Celery)](#modo-sin-sinergia-con-celery)
- [Modo completo (con Sinergia real)](#modo-completo)
- [Datos del mock](#datos-del-mock)
- [Testear un agente individual](#testear-un-agente-individual)
- [Variables mínimas por modo](#variables-mínimas)
- [Tips de debugging](#tips)

---

## Modo ultrarrápido

**Sin Celery, sin Redis, sin Sinergia** — el pipeline corre inline como una llamada HTTP normal.

### 1. `.env` mínimo

```bash
DEBUG=true
USE_MOCK_SINERGIA=true

# Una de las dos:
GOOGLE_API_KEY=tu_key_de_ai_studio
# GOOGLE_CLOUD_PROJECT=tu_proyecto_gcp  # si usas Vertex AI
```

### 2. Arranca solo la API

```bash
cd fury/app
source venv/bin/activate
python main.py
# → http://localhost:8000/docs
```

### 3. Dispara el pipeline directamente

```bash
curl -X POST http://localhost:8000/api/v2/variants/run-local \
  -H "Content-Type: application/json" \
  -d '{"id_adset": 295, "n_variants": 1}'
```

El resultado llega **en la misma respuesta HTTP** — no hay que pollear. Solo necesitas la API corriendo y un `GOOGLE_API_KEY`.

> ⚠️ `/run-local` solo está disponible con `DEBUG=true`. En producción retorna 404.

---

## Modo sin Sinergia (con Celery)

Usa el mock de Sinergia pero con la arquitectura real de Celery + Redis.

### 1. `.env`

```bash
DEBUG=true
USE_MOCK_SINERGIA=true
GOOGLE_API_KEY=tu_key
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 2. Arranca Redis

```bash
brew services start redis   # macOS
# o: redis-server
```

### 3. Terminal A — API

```bash
cd fury/app && source venv/bin/activate
python main.py
```

### 4. Terminal B — Celery (modo debug, sin fork)

```bash
cd fury/app && source venv/bin/activate
PYTHONPATH=. celery -A services.celery_app worker \
  --loglevel INFO \
  --pool solo    # sin fork → puedes usar breakpoint() / pdb
```

### 5. Dispara y pollea

```bash
# Crea el job
curl -X POST http://localhost:8000/api/v2/variants \
  -H "Content-Type: application/json" \
  -d '{"id_adset": 295, "n_variants": 1}'

# Pollea el resultado
curl http://localhost:8000/api/v2/jobs/<variant_job_id>
```

---

## Modo completo

Con Sinergia real, Celery y Redis.

### `.env` adicional

```bash
USE_MOCK_SINERGIA=false
SINERGIA_URL=http://localhost:60000      # o la URL de tu entorno
SINERGIA_SERVICE_API_KEY=hlc-fury-svc-2026
```

> Sinergia también necesita `FURY_SERVICE_API_KEY=hlc-fury-svc-2026` en su `.env`.

---

## Datos del mock

El archivo `agents/tools/mock_sinergia.py` contiene datos reales-shaped del adset 295:

| Campo | Valor |
|-------|-------|
| Producto | Nike Total 90 (retro football sneaker) |
| Campaña | "Revive the Game's Glory" |
| Brand ID | 43 |
| Audiencias | 2 segmentos masculinos 25-34 |
| Templates | 2 plantillas Abyssale |
| Idioma | English |
| Regiones | Mexico, Argentina, Brazil |

Para cambiar los datos del mock, edita directamente `agents/tools/mock_sinergia.py`.

---

## Testear un agente individual

Sin HTTP ni Celery — útil para iterar en prompts de un agente específico:

```python
# /tmp/test_agent.py
import sys, asyncio
sys.path.insert(0, "fury/app")

from google.genai import types
from core.adk_config import get_runner, session_service
from agents.data_collector_agent import data_collector_agent  # ← cambia el agente

async def main():
    runner = get_runner(data_collector_agent)
    session = await session_service.create_session(app_name="fury", user_id="dev")
    msg = types.Content(
        role="user",
        parts=[types.Part(text="id_adset=295. n_variants=1.")]
    )
    async for event in runner.run_async(
        user_id="dev", session_id=session.id, new_message=msg
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)

asyncio.run(main())
```

```bash
cd fury/app && PYTHONPATH=. python /tmp/test_agent.py
```

---

## Variables mínimas

| Variable | Ultrarrápido | Sin Sinergia | Completo |
|----------|:---:|:---:|:---:|
| `DEBUG=true` | ✅ | ✅ | — |
| `USE_MOCK_SINERGIA=true` | ✅ | ✅ | — |
| `GOOGLE_API_KEY` | ✅ | ✅ | ✅ |
| `REDIS_HOST` | — | ✅ | ✅ |
| `SINERGIA_URL` | — | — | ✅ |
| `SINERGIA_SERVICE_API_KEY` | — | — | ✅ |
| `ABYSSALE_API_KEY` | — | Paso 7 | Paso 7 |
| `LANGFUSE_*` | Opcional | Opcional | Opcional |

---

## Tips

```bash
# Ver logs de Celery en tiempo real
tail -f logs/fury/celery.log

# Verificar Redis
redis-cli ping   # → PONG

# Limpiar jobs en Redis
redis-cli FLUSHDB

# Ver resultado de un job en Redis
redis-cli GET celery-task-meta-<task_id>

# Hot-reload automático (DEBUG=true lo activa en main.py)
# Cualquier cambio en .py reinicia la API sin necesidad de hacer nada
```
