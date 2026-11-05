# main.py — webhook-router
# Cloud Function Gen2 universal para recibir webhooks de cualquier proveedor.
#
# Flujo de vida de un request:
#   1. API Gateway → CF (JWT validado por el gateway)
#   2. Extrae {servicio, version, entorno} del path
#   3. Lookup en SERVICE_REGISTRY — 400 si no existe
#   4. Carga secret de firma desde Secret Manager
#   5. Valida firma HMAC (entorno=dev → skip)
#   6. Genera idempotency_key (campo del payload o hash)
#   7. Publica en Pub/Sub wh-{servicio}-{entorno} con atributos
#   8. Retorna 200 OK inmediatamente (procesamiento async)
#
# Rutas que maneja (definidas en gateway/api-config.yaml):
#   POST /webhook/{servicio}/{version}/{entorno}
#   POST /webhook/{servicio}/{version}            → entorno="prd" por default
#   GET  /webhook/{servicio}/{version}/{entorno}  (algunos proveedores usan GET)
#   GET  /webhook/health

import hashlib
import json
import logging
import os
from typing import Any

import functions_framework
from google.auth import default as google_auth_default
from google.cloud import pubsub_v1, secretmanager

from registry import get_service_config, list_services
from verifiers import get_verifier

# ──────────────────────────────────────────────────────────────────────────────
# Logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook-router")

# ──────────────────────────────────────────────────────────────────────────────
# GCP helpers

def _get_project_id() -> str:
    pid = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if pid:
        return pid
    _, pid = google_auth_default()
    if not pid:
        raise RuntimeError("No se pudo resolver GOOGLE_CLOUD_PROJECT")
    return pid


def _get_secret(secret_name: str, project_id: str) -> str:
    """Carga la última versión de un secret desde Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8").strip()


def _get_publisher() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()

# ──────────────────────────────────────────────────────────────────────────────
# Idempotency

def _generate_idempotency_key(
    servicio: str,
    version: str,
    entorno: str,
    payload: dict,
    idempotency_field: str | None,
) -> str:
    """Genera una clave de idempotencia determinista.

    Estrategia (en orden de prioridad):
      1. Campo específico del payload (ej: appsflyer_id)
      2. Hash SHA-256 del payload completo (sort_keys para estabilidad)

    La clave se usa como atributo del mensaje Pub/Sub para que el procesador
    pueda detectar y descartar duplicados.
    """
    event_id = None

    if idempotency_field:
        # Soporta notación anidada con "." (ej: "data.id")
        parts = idempotency_field.split(".")
        value = payload
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        if value and isinstance(value, str):
            event_id = value

    if not event_id:
        # Fallback: hash del payload
        event_id = "hash:" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:24]

    return f"{servicio}:{version}:{entorno}:{event_id}"


# ──────────────────────────────────────────────────────────────────────────────
# Path parsing

def _parse_path(path: str) -> tuple[str, str, str]:
    """Extrae (servicio, version, entorno) del path del request.

    Ejemplo:
        /webhook/appsflyer/v1.0.0/dev  → ("appsflyer", "v1.0.0", "dev")
        /webhook/appsflyer/v1.0.0      → ("appsflyer", "v1.0.0", "prd")   ← default

    Entornos válidos: dev, prd
    """
    # Normalizar: quitar leading/trailing slashes
    parts = [p for p in path.strip("/").split("/") if p]
    # Esperamos: ["webhook", servicio, version] o ["webhook", servicio, version, entorno]
    if len(parts) < 3 or parts[0] != "webhook":
        raise ValueError(f"Path inválido: '{path}'. Esperado: /webhook/<servicio>/<version>[/<entorno>]")

    servicio = parts[1].lower()
    version = parts[2].lower()
    entorno = parts[3].lower() if len(parts) >= 4 else "prd"

    if entorno not in ("dev", "qas", "prd"):
        raise ValueError(f"Entorno inválido: '{entorno}'. Valores válidos: dev, qas, prd")

    return servicio, version, entorno


# ──────────────────────────────────────────────────────────────────────────────
# Request handler

@functions_framework.http
def webhook_router(request):
    """Entry point principal.

    Maneja GET y POST. Retorna JSON en todos los casos.
    Responde siempre 200 si la firma es válida (el procesamiento es async).
    """
    # Health check — sin validación
    if request.path.endswith("/health"):
        return _json_response({"status": "healthy", "services": list_services()}, 200)

    try:
        servicio, version, entorno = _parse_path(request.path)
    except ValueError as e:
        logger.warning(f"Path inválido: {e}")
        return _json_response({"error": str(e)}, 400)

    logger.info(f"Webhook recibido | servicio={servicio} version={version} entorno={entorno}")

    # ── 1. Lookup en el registro ──────────────────────────────────────────────
    config = get_service_config(servicio, version)
    if not config:
        logger.warning(f"Servicio no registrado: {servicio}@{version}")
        return _json_response(
            {"error": f"Servicio '{servicio}' versión '{version}' no registrado"},
            400,
        )

    # ── 2. Extraer payload (GET → query params, POST → body) ─────────────────
    if request.method == "GET":
        payload_dict: dict[str, Any] = dict(request.args)
        raw_body = json.dumps(payload_dict, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    else:
        raw_body = request.get_data(cache=False, as_text=False) or b""
        if raw_body:
            try:
                payload_dict = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                payload_dict = {}
        else:
            payload_dict = request.get_json(force=True, silent=True) or {}
            raw_body = json.dumps(payload_dict, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    if not raw_body:
        logger.warning("Payload vacío — ignorando")
        return _json_response({"status": "ignored", "reason": "empty_body"}, 200)

    # ── 3. Validar firma ──────────────────────────────────────────────────────
    # En entorno dev → skip firma (verify_none)
    effective_verifier = "none" if entorno == "dev" else config["verifier"]

    if effective_verifier != "none":
        signature_header = config.get("signature_header", "x-signature")
        signature = request.headers.get(signature_header, "")

        if not signature:
            logger.warning(f"Header de firma ausente: '{signature_header}'")
            return _json_response({"error": "Firma requerida"}, 401)

        try:
            project_id = _get_project_id()
            secret = _get_secret(config["secret_name"], project_id)
        except Exception as e:
            logger.error(f"Error cargando secret '{config['secret_name']}': {e}")
            return _json_response({"error": "Error interno al cargar la configuración"}, 500)

        verifier_fn = get_verifier(effective_verifier)
        if not verifier_fn(raw_body, signature, secret):
            logger.warning(f"Firma inválida | servicio={servicio} header={signature_header}")
            return _json_response({"error": "Firma inválida"}, 401)

        logger.info(f"Firma válida | servicio={servicio} verifier={effective_verifier}")
    else:
        project_id = _get_project_id()
        logger.info("Entorno dev — verificación de firma omitida")

    # ── 4. Idempotency key ────────────────────────────────────────────────────
    idempotency_key = _generate_idempotency_key(
        servicio=servicio,
        version=version,
        entorno=entorno,
        payload=payload_dict,
        idempotency_field=config.get("idempotency_field"),
    )
    logger.info(f"Idempotency key: {idempotency_key}")

    # ── 5. Publicar en Pub/Sub ────────────────────────────────────────────────
    topic_name = config["topic_pattern"].format(entorno=entorno)
    topic_path = _get_publisher().topic_path(project_id, topic_name)

    # Atributos del mensaje — el procesador los usa para contexto
    attributes = {
        "servicio": servicio,
        "version": version,
        "entorno": entorno,
        "idempotency_key": idempotency_key,
        "method": request.method,
    }

    try:
        message_id = _get_publisher().publish(
            topic_path,
            data=raw_body,
            # Pub/Sub usa ordering_key para garantizar orden dentro del topic.
            # Aquí lo usamos para agrupar eventos del mismo servicio.
            #ordering_key=f"{servicio}:{entorno}",
            **attributes,
        ).result(timeout=10)
        logger.info(f"Publicado en {topic_name} | message_id={message_id}")
    except Exception as e:
        logger.exception(f"Error publicando en Pub/Sub topic '{topic_name}': {e}")
        return _json_response({"error": "Error publicando en la cola"}, 500)

    return _json_response(
        {
            "status": "ok",
            "message_id": message_id,
            "servicio": servicio,
            "version": version,
            "entorno": entorno,
            "idempotency_key": idempotency_key,
        },
        200,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Helpers

def _json_response(body: dict, status: int):
    return (
        json.dumps(body, ensure_ascii=False),
        status,
        {"Content-Type": "application/json"},
    )
