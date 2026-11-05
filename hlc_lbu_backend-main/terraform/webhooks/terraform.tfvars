# ══════════════════════════════════════════════════════════════════════════════
# terraform.tfvars.example – HiLuca Webhook Gateway Infrastructure
#
# Copia y ajusta:
#   cp terraform.tfvars.example terraform.tfvars
#
# IMPORTANTE: terraform.tfvars nunca se sube al repo (.gitignore).
# ══════════════════════════════════════════════════════════════════════════════

# ── Proyecto GCP ──────────────────────────────────────────────────────────────
project_id     = "careful-acumen-422922-k4"
project_number = "401654669410"         # gcloud projects describe <project_id> --format='value(projectNumber)'
region         = "us-central1"

# ── Servicios de Webhook registrados ─────────────────────────────────────────
# Lista de slugs. Agrega uno por cada proveedor en registry.py.
# Por cada servicio se crean: topics Pub/Sub (dev+prd), secret, dead-letter topic.
webhook_services = ["appsflyer", "abyssale"]  # cuando agregues más, recuerda actualizar registry.py también
# webhook_services = ["appsflyer", "meta", "stripe"]  # cuando agregues más

# ── Cloud Function webhook-router ─────────────────────────────────────────────
# Genera el ZIP antes del terraform apply:
#   cd webhooks/router
#   zip -r source.zip main.py verifiers.py registry.py requirements.txt
#   md5 -q source.zip   ← usa este valor en webhook_router_source_hash
webhook_router_source_zip  = "../../webhooks/router/source.zip"
webhook_router_source_hash = "dad4478d4d829ead517057740c4a5e85"

# Instancias: 0 en dev (cold start), 1 en prd (evitar cold start)
webhook_router_min_instances = 0
webhook_router_max_instances = 10

# ── API Gateway ────────────────────────────────────────────────────────────────
# Path al OpenAPI spec (relativo a terraform/webhooks/)
gateway_openapi_spec_path = "../../webhooks/gateway/api-config.yaml"

# Incrementa en cada cambio al OpenAPI spec para crear una nueva config:
#   v1 → v2 → v3 → v4 → v5 ...
gateway_config_version = "v20"