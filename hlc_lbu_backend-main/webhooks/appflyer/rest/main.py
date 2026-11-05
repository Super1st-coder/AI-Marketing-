import os, json, logging
from typing import Any, Dict
import functions_framework
from google.cloud import pubsub_v1
from google.auth import default as google_auth_default

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_project_id() -> str:
    """Obtiene el Project ID"""
    env_pid = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if env_pid:
        logger.info(f"Project ID from environment: {env_pid}")
        return env_pid
    
    try:
        _, project_id = google_auth_default()
        if project_id:
            logger.info(f"Project ID from Google Auth: {project_id}")
            return project_id
    except Exception as e:
        logger.warning(f"Google Auth default failed: {e}")
    
    try:
        import requests
        response = requests.get('http://metadata.google.internal/computeMetadata/v1/project/project-id', 
                              headers={'Metadata-Flavor': 'Google'}, timeout=5)
        if response.status_code == 200:
            project_id = response.text
            logger.info(f"Project ID from metadata server: {project_id}")
            return project_id
    except Exception as e:
        logger.warning(f"Metadata server request failed: {e}")
    
    raise RuntimeError("No se pudo resolver el Project ID. Asegúrate de que GOOGLE_CLOUD_PROJECT esté configurado o que la función tenga permisos adecuados.")

def _get_topic_id() -> str:
    """Get the Pub/Sub topic ID from environment variables."""
    topic_id = os.environ.get("PUBSUB_TOPIC")
    if not topic_id:
        raise RuntimeError("PUBSUB_TOPIC environment variable is required")
    return topic_id

def _get_publisher_client():
    """Get a Pub/Sub publisher client with proper error handling."""
    try:
        return pubsub_v1.PublisherClient()
    except Exception as e:
        logger.error(f"Failed to create Pub/Sub client: {e}")
        raise RuntimeError(f"No se pudo crear el cliente de Pub/Sub: {e}")

@functions_framework.http
def webhook_entry_point(request):
    try:
        project_id = _get_project_id()
        topic_id = _get_topic_id()
        publisher = _get_publisher_client()
        topic_path = publisher.topic_path(project_id, topic_id)
        
        logger.info(f"Initialized with Project: {project_id}, Topic: {topic_id}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Request args: {dict(request.args)}")
        
        if request.method == "GET":
            payload = dict(request.args)
            logger.info(f"GET payload from query params: {payload}")
            body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        else:
            body = request.get_data(cache=False, as_text=False) or b""
            if body:
                logger.info(f"Payload RAW recibido: {len(body)} bytes")
                try:
                    logger.info(f"Preview JSON: {json.loads(body.decode('utf-8'))}")
                except Exception:
                    logger.info("RAW no es JSON válido (lo publicaremos tal cual).")
            else:
                payload: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
                body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                logger.info(f"Payload vacío en RAW; construidos {len(body)} bytes desde get_json().")

        if not body:
            logger.warning("Cuerpo vacío tras ambos métodos; NO se publica en Pub/Sub.")
            return (json.dumps({"status": "ignored", "reason": "empty_body"}), 200,
                    {"Content-Type": "application/json"})

        message_id = publisher.publish(topic_path, body).result()
        logger.info(f"Mensaje publicado con ID: {message_id}")
        return (json.dumps({"status": "ok", "message_id": message_id}), 200,
                {"Content-Type": "application/json"})
    except Exception as e:
        logger.exception("Error publicando mensaje")
        return (json.dumps({"status": "error", "error": str(e)}), 500,
                {"Content-Type": "application/json"})
