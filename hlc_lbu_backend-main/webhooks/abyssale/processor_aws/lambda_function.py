import os
import json
import logging
import requests
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

# Host headers esperados por el Application Load Balancer
HOST_HEADERS = {
    "dev": "api-dev.hiluca.com",
    "qas": "api-qas.hiluca.com",
    "prd": "api.hiluca.com"
} 

def lambda_handler(event: dict, context: Any) -> None:
    logger.info("Event received (SNS)")
    
    if not event.get("Records"):
        logger.warning("No Records found in the event")
        return
        
    for record in event["Records"]:
        try:
            process_record(record)
        except Exception as e:
            logger.error(f"Failed to process record: {e}")
            # En SNS, lanzar excepcion reencola el mensaje según las Dead Letter Queue o retry policies.
            # Puedes optar por capturarlo o dejarlo subir.
            raise e

def process_record(record: dict):
    sns_data = record.get("Sns", {})
    message_body = sns_data.get("Message", "")
    message_attributes = sns_data.get("MessageAttributes", {})

    # ── Atributos del router (trazabilidad) ───────────────────────────────────
    # Helper para extraer el "Value" de un atributo SNS
    def get_attr(key: str, default: str) -> str:
        attr = message_attributes.get(key)
        if attr and "Value" in attr:
            return attr["Value"]
        return default

    servicio        = get_attr("servicio", "abyssale")
    version         = get_attr("version", "v1.0.0")
    entorno         = get_attr("entorno", "prd")
    idempotency_key = get_attr("idempotency_key", "")
    method          = get_attr("method", "POST")

    logger.info(
        f"Routing | servicio={servicio} version={version} "
        f"entorno={entorno} idempotency_key={idempotency_key} method={method}"
    )

    # ── Decodificar payload ───────────────────────────────────────────────────
    if not message_body.strip():
        logger.warning("Payload vacío; se ignora.")
        return

    try:
        # En SNS el mensaje suele venir como texto crudo JSON (no base64 como en PubSub puro, 
        # a menos que el publisher lo codifique explicitamente)
        payload = json.loads(message_body)
        logger.info(f"Decoded JSON payload keys: {list(payload.keys())}")
    except Exception:
        logger.info("Payload no es JSON; lo envolvemos como texto crudo.")
        payload = {"raw": message_body}

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

    host_header = HOST_HEADERS.get(entorno)
    if not host_header:
        logger.error(f"Entorno desconocido: {entorno}")
        return

    alb_dns = os.environ.get("ALB_DNS_NAME")
    
    # En prd podríamos ir directo a la URL publica HTTPS, pero si usamos ALB interno o publico,
    # construimos la URL usando el ALB.
    if alb_dns:
        # Usar HTTP contra el ALB interno/público de AWS
        url = f"http://{alb_dns}/api/v2/application/hiluca/brand/ad/media/visuals/platform/visual_generation_hook"
    else:
        # Fallback por si no se pasa ALB_DNS_NAME (ej: test local o prd publico directo)
        scheme = "https" if entorno == "prd" else "http"
        url = f"{scheme}://{host_header}/api/v2/application/hiluca/brand/ad/media/visuals/platform/visual_generation_hook"

    logger.info(f"Enviando POST a {url} con Host: {host_header}")

    try:
        # Hacer el POST con el payload como JSON e inyectar el Host header
        headers = {"Host": host_header}
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()  # Lanza excepción si no es 2xx
        logger.info(f"POST exitoso: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en POST a {url}: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error procesando evento: {e}")
        raise e
