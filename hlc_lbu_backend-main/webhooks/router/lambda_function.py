# lambda_function.py — webhook-router para AWS
# Cloud Function Gen2 universal adaptada para AWS Lambda + API Gateway (HTTP API).
#
# Flujo de vida de un request:
#   1. API Gateway → Lambda Function (Evento HTTP API v2.0)
#   2. Extrae {servicio, version, entorno} del path
#   3. Lookup en SERVICE_REGISTRY — 400 si no existe
#   4. Carga secret de firma desde AWS Secrets Manager
#   5. Valida firma HMAC (entorno=dev → skip)
#   6. Genera idempotency_key (campo del payload o hash)
#   7. Publica en AWS SNS (Topic: wh-{servicio}-{entorno})
#   8. Retorna 200 OK inmediatamente (procesamiento async)

import hashlib
import json
import logging
import os
import boto3
from typing import Any

from registry import get_service_config, list_services
from verifiers import get_verifier

# ──────────────────────────────────────────────────────────────────────────────
# Logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook-router")
logger.setLevel(logging.INFO)

# ──────────────────────────────────────────────────────────────────────────────
# AWS helpers

# Inicializar clientes fuera del handler para reutilización (cold start)
sns_client = boto3.client('sns')
secrets_client = boto3.client('secretsmanager') 

def _get_aws_account_id() -> str:
    return boto3.client('sts').get_caller_identity().get('Account')

def _get_aws_region() -> str:
    return os.environ.get('AWS_REGION_NAME', 'us-east-2')

def _get_secret(secret_name: str) -> str:
    """Carga un secret desde AWS Secrets Manager."""
    # Prefix se define en el entorno de terraform (ej: hiluca-lbu-dev)
    prefix = os.environ.get("PREFIX", "hiluca-lbu-dev")
    full_secret_name = f"{prefix}-{secret_name}"
    
    response = secrets_client.get_secret_value(SecretId=full_secret_name)
    # Puede ser SecretString o SecretBinary
    if 'SecretString' in response:
        return response['SecretString'].strip()
    else:
        return response['SecretBinary'].decode('utf-8').strip()

# ──────────────────────────────────────────────────────────────────────────────
# Idempotency

def _generate_idempotency_key(
    servicio: str,
    version: str,
    entorno: str,
    payload: dict,
    idempotency_field: str | None,
) -> str:
    """Genera una clave de idempotencia determinista."""
    event_id = None

    if idempotency_field:
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
        event_id = "hash:" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:24]

    return f"{servicio}:{version}:{entorno}:{event_id}"

# ──────────────────────────────────────────────────────────────────────────────
# Path parsing

def _parse_path(path: str) -> tuple[str, str, str]:
    """Extrae (servicio, version, entorno) del path.
    Ejemplo: /webhook/appsflyer/v1.0.0/dev  → ("appsflyer", "v1.0.0", "dev")
    """
    parts = [p for p in path.strip("/").split("/") if p]
    if len(parts) < 3 or parts[0] != "webhook":
        raise ValueError(f"Path inválido: '{path}'. Esperado: /webhook/<servicio>/<version>[/<entorno>]")

    servicio = parts[1].lower()
    version = parts[2].lower()
    entorno = parts[3].lower() if len(parts) >= 4 else "prd"

    if entorno not in ("dev", "qas", "prd"):
        raise ValueError(f"Entorno inválido: '{entorno}'. Valores válidos: dev, qas, prd")

    return servicio, version, entorno

# ──────────────────────────────────────────────────────────────────────────────
# Request handler (AWS Lambda Entrypoint)

def lambda_handler(event: dict, context: Any) -> dict:
    """Entry point para AWS Lambda invocada por API Gateway (HTTP API v2)."""
    
    # 1. Extraer Request Info (HTTP API Payload Format 2.0)
    raw_path = event.get('rawPath', '/')
    method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    
    if raw_path.endswith("/health"):
        return _json_response({"status": "healthy", "services": list_services()}, 200)

    try:
        servicio, version, entorno = _parse_path(raw_path)
    except ValueError as e:
        logger.warning(f"Path inválido: {e}")
        return _json_response({"error": str(e)}, 400)

    logger.info(f"Webhook recibido | servicio={servicio} version={version} entorno={entorno} method={method}")

    # 2. Lookup en el registro
    config = get_service_config(servicio, version)
    if not config:
        logger.warning(f"Servicio no registrado: {servicio}@{version}")
        return _json_response(
            {"error": f"Servicio '{servicio}' versión '{version}' no registrado"},
            400,
        )

    # 3. Extraer headers y payload
    # API Gateway manda headers en minúsculas en HTTP API v2
    headers = event.get('headers', {})
    
    if method == "GET":
        # Query params
        payload_dict = event.get('queryStringParameters', {})
        raw_body_str = json.dumps(payload_dict, separators=(",", ":"), ensure_ascii=False)
        raw_body_bytes = raw_body_str.encode("utf-8")
    else:
        # POST/PUT: body raw (si isBase64Encoded es true, hay que decodificar, API Gtw lo manda como string)
        import base64
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            raw_body_bytes = base64.b64decode(body)
        else:
            raw_body_bytes = body.encode('utf-8')
            
        try:
            payload_dict = json.loads(raw_body_bytes.decode("utf-8")) if raw_body_bytes else {}
        except json.JSONDecodeError:
            payload_dict = {}

    if not raw_body_bytes:
        logger.warning("Payload vacío — ignorando")
        return _json_response({"status": "ignored", "reason": "empty_body"}, 200)

    # 4. Validar firma
    effective_verifier = "none" if entorno == "dev" else config["verifier"]

    if effective_verifier != "none":
        signature_header = config.get("signature_header", "x-signature").lower()
        signature = headers.get(signature_header, "")

        if not signature:
            logger.warning(f"Header de firma ausente: '{signature_header}'")
            return _json_response({"error": "Firma requerida"}, 401)

        try:
            secret = _get_secret(config["secret_name"])
        except Exception as e:
            logger.error(f"Error cargando secret '{config['secret_name']}': {e}")
            return _json_response({"error": "Error interno al cargar la configuración"}, 500)

        verifier_fn = get_verifier(effective_verifier)
        if not verifier_fn(raw_body_bytes, signature, secret):
            logger.warning(f"Firma inválida | servicio={servicio} header={signature_header}")
            return _json_response({"error": "Firma inválida"}, 401)

        logger.info(f"Firma válida | servicio={servicio} verifier={effective_verifier}")
    else:
        logger.info("Entorno dev — verificación de firma omitida")

    # 5. Idempotency key
    idempotency_key = _generate_idempotency_key(
        servicio=servicio,
        version=version,
        entorno=entorno,
        payload=payload_dict,
        idempotency_field=config.get("idempotency_field"),
    )
    logger.info(f"Idempotency key: {idempotency_key}")

    # 6. Publicar en AWS SNS
    prefix = os.environ.get("PREFIX", "hiluca-lbu-dev")
    topic_name = config["topic_pattern"].format(entorno=entorno)
    # Formato ARN SNS: arn:aws:sns:REGION:ACCOUNT:TOPIC_NAME
    # Ejemplo topic_name: wh-appsflyer-dev -> prefix-wh-appsflyer-dev
    full_topic_name = f"{prefix}-{topic_name}"
    topic_arn = f"arn:aws:sns:{_get_aws_region()}:{_get_aws_account_id()}:{full_topic_name}"

    attributes = {
        "servicio": {"DataType": "String", "StringValue": servicio},
        "version": {"DataType": "String", "StringValue": version},
        "entorno": {"DataType": "String", "StringValue": entorno},
        "idempotency_key": {"DataType": "String", "StringValue": idempotency_key},
        "method": {"DataType": "String", "StringValue": method},
    }

    try:
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=raw_body_bytes.decode('utf-8'),
            MessageAttributes=attributes
        )
        message_id = response.get('MessageId')
        logger.info(f"Publicado en SNS {full_topic_name} | message_id={message_id}")
    except Exception as e:
        logger.exception(f"Error publicando en SNS topic '{full_topic_name}': {e}")
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

def _json_response(body: dict, status: int) -> dict:
    """Retorna un diccionario en el formato esperado por AWS API Gateway HTTP API v2"""
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }
