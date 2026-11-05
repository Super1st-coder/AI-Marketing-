import os
import json
import base64
import logging
from typing import Any, Dict
import functions_framework

from google.cloud import bigquery
from google.auth import default as google_auth_default
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

FERNET_KEY = b"VxStP99cf4TUnH3uWcQhZoPGDr5HDuV5wAJyCJZFmUw="

def _get_project_id() -> str:
    pid = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if pid:
        return pid
    _, pid = google_auth_default()
    if not pid:
        raise RuntimeError("No se pudo resolver GOOGLE_CLOUD_PROJECT")
    return pid

def _get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=_get_project_id())

def _get_bq_target() -> tuple[str, str]:
    dataset = os.getenv("BIGQUERY_DATASET")
    table = os.getenv("BIGQUERY_TABLE")
    if not dataset or not table:
        raise RuntimeError("Faltan BIGQUERY_DATASET o BIGQUERY_TABLE")
    return dataset, table

def _get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    key = FERNET_KEY
    if not key:
        raise RuntimeError("ENCRYPTION_KEY no está configurada")
    try:
        return Fernet(key.encode() if not key.startswith("gAAAA") else key) \
               if isinstance(key, str) else Fernet(key)
    except Exception as e:
        raise RuntimeError(f"ENCRYPTION_KEY inválida: {e}")

def encrypt_str(plain: str) -> str:
    """Devuelve 'enc:v1:<base64>' usando Fernet."""
    f = _get_fernet()
    token = f.encrypt(plain.encode("utf-8"))
    return f"enc:v1:{token.decode('utf-8')}"

SENSITIVE_FIELDS = {
    "ip", "advertising_id", "af_user_id", "idfa", "idfv", "gaid", "email",
    "phone", "android_id", "customer_user_id"
}

def encrypt_payload(obj: Any) -> Any:
    """Cifra recursivamente"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in SENSITIVE_FIELDS and isinstance(v, str) and v:
                try:
                    out[k] = encrypt_str(v)
                except Exception as e:
                    logger.warning(f"No se pudo cifrar {k}: {e}; se deja vacío.")
                    out[k] = None
            else:
                out[k] = encrypt_payload(v)
        return out
    elif isinstance(obj, list):
        return [encrypt_payload(x) for x in obj]
    else:
        return obj

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
    # El webhook-router publica estos atributos en cada mensaje.
    # Los usamos para logging estructurado; en el futuro pueden usarse
    # para idempotency checks en BigQuery.
    attributes = message.get("attributes", {})
    servicio        = attributes.get("servicio", "appsflyer")    # retrocompat
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

    # Inyectar metadatos de routing en el payload para que procesar_evento
    # pueda incluirlos en BigQuery si es necesario
    payload["_routing"] = {
        "servicio": servicio,
        "version": version,
        "entorno": entorno,
        "idempotency_key": idempotency_key,
    }

    procesar_evento(payload)


def procesar_evento(payload):
    """
    Procesa el evento de AppsFlyer y lo inserta en BigQuery con columnas estructuradas
    """
    logger.info(f"Procesando evento: {payload}")

    logger.info(f"Proyecto: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    logger.info(f"Dataset: {os.getenv('BIGQUERY_DATASET')}")
    logger.info(f"Table: {os.getenv('BIGQUERY_TABLE')}")

    # 1) Encripta campos sensibles
    encrypted = encrypt_payload(payload)

    # 2) Extrae campos de atribución
    af_attribution = payload.get("af_attribution", {})
    media_source = af_attribution.get("media_source") if isinstance(af_attribution, dict) else None
    is_retargeting = af_attribution.get("is_retargeting") if isinstance(af_attribution, dict) else None

    # 3) Extrae campos de even_value JSON
    even_value_data = _parse_even_value(payload.get("even_value"))

    # 3) Prepara registro estructurado para BQ
    row = {
        "event_time": _parse_timestamp(payload.get("event_time") or payload.get("install_time")),
        "event": payload.get("event"),
        "app_id": payload.get("app_id"),
        "platform": payload.get("platform"),
        "install_time": _parse_timestamp(payload.get("install_time")),
        
        "event_name": payload.get("event_name"),
        "event_revenue": payload.get("event_revenue"),
        "event_revenue_usd": payload.get("event_revenue_usd"),
        "event_revenue_currency": payload.get("event_revenue_currency"),
        "even_value": payload.get("even_value"),
        
        "transaction_amount": even_value_data.get("TRANSACTION_AMOUNT"),
        "transaction_timestamp": even_value_data.get("TIMESTAMP"),
        "bank_name": even_value_data.get("BANKNAME"),
        "brand_type": even_value_data.get("BRANDTYPE"),
        "transaction_type": even_value_data.get("TRANSACTION_TYPE"),
        "payment_method": even_value_data.get("PAYMENT_METHOD"),
        
        "app_name": payload.get("app_name"),
        "app_version": payload.get("app_version"),
        "sdk_version": payload.get("sdk_version"),
        
        "android_device_id": encrypted.get("android_device_id"),
        "appsflyer_id": payload.get("appsflyer_id"),
        "af_user_id": encrypted.get("af_user_id"),
        "advertising_id": encrypted.get("advertising_id"),
        "android_id": encrypted.get("android_id"),
        "customer_user_id": encrypted.get("customer_user_id"),
        "idfa": encrypted.get("idfa"),
        "idfv": encrypted.get("idfv"),
        "gaid": encrypted.get("gaid"),
        
        "country_code": payload.get("country_code"),
        "language": payload.get("language"),
        "ip": encrypted.get("ip"),
        
        "site_id": payload.get("site_id"),
        "ad": payload.get("ad"),
        "ad_is": payload.get("ad_is"),
        "adset": payload.get("adset"),
        "adset_id": payload.get("adset_id"),
        "campaign": payload.get("campaign"),
        "click_id": payload.get("click_id"),
        
        "cost_currency": payload.get("cost_currency"),
        "cost_model": payload.get("cost_model"),
        "cost_value": payload.get("cost_value"),
        
        "af_attribution": json.dumps(af_attribution) if af_attribution else None,
        "media_source": media_source,
        "is_retargeting": is_retargeting,
        
        "payload_json": json.dumps(encrypted, ensure_ascii=False),
    }

    logger.info(f"Row: {row}")

    # 4) Inserta en BigQuery
    dataset, table = _get_bq_target()
    table_id = f"{_get_project_id()}.{dataset}.{table}"

    bq = _get_bq_client()
    errors = bq.insert_rows_json(table_id, [row])
    if errors:
        logger.error(f"Errores insertando en BigQuery: {errors}")
    else:
        logger.info(f"Insertado en {table_id}")


def _parse_even_value(even_value_str):
    """
    Extrae campos del JSON en even_value
    """
    if not even_value_str or even_value_str == "N/A":
        return {}
    
    try:
        if isinstance(even_value_str, str):
            return json.loads(even_value_str)
        return even_value_str if isinstance(even_value_str, dict) else {}
    except Exception as e:
        logger.warning(f"No se pudo parsear even_value '{even_value_str}': {e}")
        return {}


def _parse_timestamp(timestamp_str):
    """
    Convierte string de timestamp a TIMESTAMP de BigQuery
    """
    if not timestamp_str:
        return None
    
    try:
        if isinstance(timestamp_str, str):
            if 'T' in timestamp_str and ('+' in timestamp_str or 'Z' in timestamp_str):
                from datetime import datetime
                clean_timestamp = timestamp_str.split('+')[0].split('Z')[0]
                return datetime.fromisoformat(clean_timestamp).isoformat()
            elif ' ' in timestamp_str and ':' in timestamp_str:
                return timestamp_str
        return timestamp_str
    except Exception as e:
        logger.warning(f"No se pudo parsear timestamp '{timestamp_str}': {e}")
        return None
