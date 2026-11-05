import os
import json
import base64
import logging
import requests
from typing import Any, Dict
import functions_framework

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

# URLs por entorno para el POST
URLS = {
    "dev": "http://10.128.0.12:60002/api/v2/application/hiluca/brand/ad/media/visuals/platform/visual_generation_hook",
    "qas": "http://10.128.0.12:60004/api/v2/application/hiluca/brand/ad/media/visuals/platform/visual_generation_hook",
    "prd": "https://api.hiluca.com/api/v2/application/hiluca/brand/ad/media/visuals/platform/visual_generation_hook"
}

@functions_framework.cloud_event
def pubsub_handler(cloud_event):
    logger.info("Event received (CloudEvent)")

    if not hasattr(cloud_event, 'data') or not isinstance(cloud_event.data, dict):
        logger.error("Invalid CloudEvent data")
        return

    message = cloud_event.data.get("message", {})
    if "data" not in message:
        logger.error("Missing 'message.data'")
        return

    # ── Atributos del router (trazabilidad) ───────────────────────────────────
    attributes = message.get("attributes", {})
    servicio        = attributes.get("servicio", "abyssale")
    version         = attributes.get("version", "v1.0.0")
    entorno         = attributes.get("entorno", "prd")
    idempotency_key = attributes.get("idempotency_key", "")
    method          = attributes.get("method", "POST")

    logger.info(
        f"Routing | servicio={servicio} version={version} "
        f"entorno={entorno} idempotency_key={idempotency_key} method={method}"
    )

    # ── Decodificar payload ───────────────────────────────────────────────────
    data_b64 = message.get("data", "")
    decoded = base64.b64decode(data_b64 or "").decode("utf-8", errors="replace")

    if not decoded.strip():
        logger.warning("Payload vacío tras base64; se ignora.")
        return

    try:
        payload = json.loads(decoded)
        logger.info(f"Decoded JSON payload keys: {list(payload.keys())}")
    except Exception:
        logger.info("Payload no es JSON; lo envolvemos como texto crudo.")
        payload = {"raw": decoded}

    # Inyectar metadatos de routing en el payload
    payload["_routing"] = {
        "servicio": servicio,
        "version": version,
        "entorno": entorno,
        "idempotency_key": idempotency_key,
    }

    procesar_evento(payload, entorno)


def procesar_evento(payload: Dict[str, Any], entorno: str):
    """
    Procesa el evento de Abyssale y hace un POST a la URL correspondiente
    """
    logger.info(f"Procesando evento Abyssale: {payload}")

    # Determinar la URL basada en el entorno
    url = URLS.get(entorno)
    if not url:
        logger.error(f"Entorno desconocido: {entorno}")
        return

    logger.info(f"Enviando POST a {url}")

    try:
        # Hacer el POST con el payload como JSON
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()  # Lanza excepción si no es 2xx
        logger.info(f"POST exitoso: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en POST a {url}: {e}")
    except Exception as e:
        logger.error(f"Error procesando evento: {e}")