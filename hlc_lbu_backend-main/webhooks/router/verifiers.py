# verifiers.py
# Verificadores de firma por proveedor de webhook.
# Adaptado de reference/src/webhook_handler.py
#
# Fuentes de referencia:
#   AppsFlyer: https://support.appsflyer.com/hc/en-us/articles/207032076
#   Stripe:    https://stripe.com/docs/webhooks/signatures
#   Meta:      https://developers.facebook.com/docs/graph-api/webhooks/getting-started
#   Abyssale:  

import hashlib
import hmac
import logging
import time

logger = logging.getLogger(__name__)


def verify_hmac_sha256(payload: bytes, signature: str, secret: str) -> bool:
    """Verificación genérica HMAC-SHA256.

    Funciona para: AppsFlyer, MercadoPago, Meta (x-hub-signature-256 sin prefijo),
    y la mayoría de PSPs.

    El header puede llegar como:
      - hex puro:        "abc123..."
      - con prefijo sha256=  "sha256=abc123..."  (Meta)
    """
    if not secret:
        logger.warning("verify_hmac_sha256: secret vacío — rechazando")
        return False

    # Normalizar: quitar prefijo "sha256=" si Meta lo envía
    sig = signature.removeprefix("sha256=").strip()

    computed = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    try:
        return hmac.compare_digest(computed, sig)
    except Exception:
        return False


def verify_hmac_sha512(payload: bytes, signature: str, secret: str) -> bool:
    """HMAC-SHA512 para proveedores que lo usan."""
    if not secret:
        logger.warning("verify_hmac_sha512: secret vacío — rechazando")
        return False

    computed = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha512,
    ).hexdigest()

    try:
        return hmac.compare_digest(computed, signature.strip())
    except Exception:
        return False


def verify_stripe(payload: bytes, signature: str, secret: str) -> bool:
    """Verificación Stripe — HMAC-SHA256 con prefijo de timestamp.

    Stripe-Signature header format:
        t=<unix_timestamp>,v1=<hex_signature>

    Rechaza si el timestamp tiene más de 5 minutos de diferencia (anti-replay).
    """
    if not secret:
        logger.warning("verify_stripe: secret vacío — rechazando")
        return False
    try:
        parts = dict(item.split("=", 1) for item in signature.split(","))
        timestamp = parts.get("t", "")
        expected_sig = parts.get("v1", "")

        # Protección anti-replay: tolerancia de 5 minutos
        if abs(time.time() - int(timestamp)) > 300:
            logger.warning("verify_stripe: timestamp fuera de ventana (>5 min)")
            return False

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        computed = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, expected_sig)
    except (ValueError, KeyError) as e:
        logger.warning(f"verify_stripe: error parseando firma — {e}")
        return False


def verify_none(payload: bytes, signature: str, secret: str) -> bool:
    """Sin verificación de firma.

    SOLO para entorno dev/pruebas. Nunca usar en prd.
    El router garantiza que esto solo se activa cuando entorno='dev'.
    """
    logger.warning("⚠️  verify_none activo — entorno dev, sin validación de firma")
    return True


def verify_abyssale(payload: bytes, signature: str, secret: str) -> bool:
    """Verificación Abyssale — valida que el header X-Referer contenga 'api.abyssale.com'.

    El parámetro 'signature' debe ser el valor del header X-Referer del request.
    """
    if not signature:
        logger.warning("verify_abyssale: header X-Referer vacío — rechazando")
        return False

    if "api.abyssale.com" in signature:
        return True
    else:
        logger.warning(f"verify_abyssale: X-Referer '{signature}' no contiene 'api.abyssale.com'")
        return False


# Mapa verifier_type → función
VERIFIERS: dict[str, callable] = {
    "hmac_sha256": verify_hmac_sha256,
    "hmac_sha512": verify_hmac_sha512,
    "stripe": verify_stripe,
    "abyssale": verify_abyssale,
    "none": verify_none,
}


def get_verifier(verifier_type: str) -> callable:
    """Retorna la función verificadora para el tipo dado.

    Si el tipo no existe, lanza ValueError.
    """
    fn = VERIFIERS.get(verifier_type)
    if fn is None:
        raise ValueError(
            f"Verifier desconocido: '{verifier_type}'. "
            f"Opciones válidas: {list(VERIFIERS.keys())}"
        )
    return fn
