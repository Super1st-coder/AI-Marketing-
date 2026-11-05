# registry.py
# Registro de servicios para el webhook-router.
#
# Para agregar un nuevo proveedor:
#   1. Agrega una entrada en SERVICE_REGISTRY con su slug y versión
#   2. Crea el secret en Secret Manager: wh-secret-{servicio}
#   3. Crea el Pub/Sub topic: wh-{servicio}-{entorno}
#   4. Despliega la CF procesadora: wh-proc-{servicio}
#
# Convención de nombres Pub/Sub:  wh-{servicio}-{entorno}
#   Ejemplos: wh-appsflyer-prd, wh-appsflyer-dev, wh-meta-prd

from typing import Literal

# Métodos de verificación de firma soportados
VerifierType = Literal["hmac_sha256", "hmac_sha512", "stripe", "none", "abyssale"]

# Formato del registro:
# {
#   "<servicio>": {
#     "<version>": {
#       "verifier":          VerifierType,
#       "secret_name":       str,        # nombre en Secret Manager (sin proyecto)
#       "signature_header":  str,        # header HTTP donde viene la firma
#       "idempotency_field": str | None, # campo del payload para idempotency key
#                                        # None = usa hash del payload completo
#       "topic_pattern":     str,        # f-string con {entorno}
#     }
#   }
# }

SERVICE_REGISTRY: dict[str, dict[str, dict]] = {

    # ──────────────────────────────────────────────────────────────────────────
    # AppsFlyer
    # Docs: https://support.appsflyer.com/hc/en-us/articles/207032076
    # Firma: HMAC-SHA256 en header "X-Signature" (hex-encoded)
    # ──────────────────────────────────────────────────────────────────────────
    "appsflyer": {
        "v1.0.0": {
            "verifier": "hmac_sha256",
            "secret_name": "wh-secret-appsflyer",   # Secret Manager key
            "signature_header": "x-signature",       # header en minúsculas
            "idempotency_field": "appsflyer_id",     # campo en el payload
            "topic_pattern": "wh-appsflyer-{entorno}",
        },
    },

    # ──────────────────────────────────────────────────────────────────────────
    # Abyssale — PLACEHOLDER
    # ──────────────────────────────────────────────────────────────────────────
    "abyssale": {
        "v1.0.0": {
            "verifier": "abyssale",
            "secret_name": "wh-secret-abyssale",
            "signature_header": "X-Referer",
            "idempotency_field": "generation_request_id",
            "topic_pattern": "wh-abyssale-{entorno}",
        },
    },

    # ──────────────────────────────────────────────────────────────────────────
    # Abyssale — Visual Edit
    # ──────────────────────────────────────────────────────────────────────────
    "abyssale-visual-edit": {
        "v1.0.0": {
            "verifier": "abyssale",
            "secret_name": "wh-secret-abyssale",
            "signature_header": "X-Referer",
            "idempotency_field": "generation_request_id",
            "topic_pattern": "wh-abyssale-visual-edit-{entorno}",
        },
    },

    # ──────────────────────────────────────────────────────────────────────────
    # Meta (Facebook/Instagram) — PLACEHOLDER
    # Descomenta y configura cuando sea necesario
    # ──────────────────────────────────────────────────────────────────────────
    # "meta": {
    #     "v1.0.0": {
    #         "verifier": "hmac_sha256",
    #         "secret_name": "wh-secret-meta",
    #         "signature_header": "x-hub-signature-256",  # contiene "sha256=<hash>"
    #         "idempotency_field": None,  # usa hash del payload
    #         "topic_pattern": "wh-meta-{entorno}",
    #     },
    # },

    # ──────────────────────────────────────────────────────────────────────────
    # Stripe — PLACEHOLDER
    # ──────────────────────────────────────────────────────────────────────────
    # "stripe": {
    #     "v1.0.0": {
    #         "verifier": "stripe",
    #         "secret_name": "wh-secret-stripe",
    #         "signature_header": "stripe-signature",
    #         "idempotency_field": "id",
    #         "topic_pattern": "wh-stripe-{entorno}",
    #     },
    # },
}


def get_service_config(servicio: str, version: str) -> dict | None:
    """Retorna la configuración del servicio/versión o None si no existe."""
    return SERVICE_REGISTRY.get(servicio, {}).get(version)


def list_services() -> list[dict]:
    """Lista todos los servicios y versiones registrados (para el health check)."""
    result = []
    for servicio, versions in SERVICE_REGISTRY.items():
        for version in versions:
            result.append({"servicio": servicio, "version": version})
    return result
