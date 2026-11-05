# ══════════════════════════════════════════════════════════════════════════════
# main.tf – HiLuca Webhook Gateway Infrastructure
#
# Crea la infraestructura del servicio de webhooks reutilizable:
#   - APIs habilitadas (cloudfunctions, apigateway, pubsub, etc.)
#   - Service Account dedicado para webhook-router
#   - Secret Manager (signing secrets por servicio)
#   - Pub/Sub topics (wh-{servicio}-{entorno}) + dead-letter topics
#   - Pub/Sub subscriptions (push → CF procesadoras)
#   - Cloud Function Gen2: webhook-router
#   - API Gateway: hiluca-webhook-gateway + config + gateway
#
# Uso (comparte workspace con infra/):
#   terraform workspace select dev
#   terraform apply -var-file=env/dev.tfvars
#
# Nota: Este módulo es GLOBAL (solo 1 router para dev+prd).
# El entorno se controla en runtime vía el path URL, no vía workspace.
# ══════════════════════════════════════════════════════════════════════════════

locals {
  project = var.project_id
  region  = var.region

  labels = {
    app        = "hiluca-webhooks"
    managed_by = "terraform"
  }

  # Servicios registrados — agregar aquí al incorporar nuevos webhooks
  # Generates: wh-{servicio}-dev  y  wh-{servicio}-prd
  webhook_services = var.webhook_services
  entornos         = ["dev", "qas", "prd"]

  # Producto cartesiano: {servicio} × {entorno}
  service_env_pairs = {
    for pair in setproduct(local.webhook_services, local.entornos) :
    "${pair[0]}-${pair[1]}" => {
      servicio = pair[0]
      entorno  = pair[1]
    }
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# APIs requeridas
# ══════════════════════════════════════════════════════════════════════════════

resource "google_project_service" "webhook_apis" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "run.googleapis.com", # Cloud Functions Gen2 usa Cloud Run
    "apigateway.googleapis.com",
    "servicemanagement.googleapis.com",
    "servicecontrol.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "eventarc.googleapis.com",
    "logging.googleapis.com",
  ])
  project            = local.project
  service            = each.value
  disable_on_destroy = false
}

# ══════════════════════════════════════════════════════════════════════════════
# Service Account — webhook-router
# SA único, no por ambiente (el router es global)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_service_account" "webhook_router_sa" {
  account_id   = "webhook-router-sa"
  display_name = "HiLuca Webhook Router – Cloud Function SA"
  project      = local.project
  depends_on   = [google_project_service.webhook_apis]
}

resource "google_service_account" "webhook_gateway_sa" {
  account_id   = "webhook-gateway-sa"
  display_name = "HiLuca Webhook Gateway – backend auth service account"
  project      = local.project
  depends_on   = [google_project_service.webhook_apis]
}

# Publicar en Pub/Sub
resource "google_project_iam_member" "router_pubsub_publisher" {
  project = local.project
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.webhook_router_sa.email}"
}

# Leer secrets (signing secrets por servicio)
resource "google_project_iam_member" "router_secret_accessor" {
  project = local.project
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.webhook_router_sa.email}"
}

# Escribir logs
resource "google_project_iam_member" "router_log_writer" {
  project = local.project
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.webhook_router_sa.email}"
}

# Invocar en Pub/Sub
resource "google_project_iam_member" "router_pubsub_invoker" {
  project = local.project
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.webhook_router_sa.email}"
}

# ══════════════════════════════════════════════════════════════════════════════
# Secret Manager — Signing secrets por servicio
# El CONTENIDO del secret se sube manualmente (no Terraform):
#   echo -n "TU_SECRET" | gcloud secrets versions add wh-secret-appsflyer \
#     --data-file=- --project=<PROJECT_ID>
# ══════════════════════════════════════════════════════════════════════════════

resource "google_secret_manager_secret" "webhook_signing_secret" {
  for_each  = toset(local.webhook_services)
  secret_id = "wh-secret-${each.value}"
  project   = local.project
  labels    = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.webhook_apis]
}

# ══════════════════════════════════════════════════════════════════════════════
# Pub/Sub — Dead-letter topics (uno por servicio, comparte dev+prd)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_pubsub_topic" "webhook_dead_letter" {
  for_each = toset(local.webhook_services)
  name     = "wh-${each.value}-dead-letter"
  project  = local.project
  labels   = local.labels

  message_retention_duration = "604800s" # 7 días

  depends_on = [google_project_service.webhook_apis]
}

# ══════════════════════════════════════════════════════════════════════════════
# Pub/Sub — Topics principales: wh-{servicio}-{entorno}
# ══════════════════════════════════════════════════════════════════════════════

resource "google_pubsub_topic" "webhook_topic" {
  for_each = local.service_env_pairs
  name     = "wh-${each.value.servicio}-${each.value.entorno}"
  project  = local.project
  labels   = local.labels

  # Retención: 7 días (permite reintentos manuales)
  message_retention_duration = "604800s"

  depends_on = [google_project_service.webhook_apis]
}

# ══════════════════════════════════════════════════════════════════════════════
# Pub/Sub — Subscriptions con dead-letter
# Una subscription por topic. Las CF procesadoras usan push o pull según config.
# Por defecto: pull (la CF se despliega con trigger-topic en gcloud CLI).
# Aquí creamos las suscripciones de auditoría con dead-letter.
# ══════════════════════════════════════════════════════════════════════════════

resource "google_pubsub_subscription" "webhook_subscription" {
  for_each = local.service_env_pairs
  name     = "wh-sub-${each.value.servicio}-${each.value.entorno}"
  topic    = google_pubsub_topic.webhook_topic[each.key].name
  project  = local.project
  labels   = local.labels

  # Retención de mensajes no entregados: 7 días
  message_retention_duration = "604800s"

  # Tiempo de espera antes de reintento
  ack_deadline_seconds = 60

  # Política de reintentos exponencial
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s" # 10 min máximo entre reintentos
  }

  # Dead-letter después de 5 intentos fallidos
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.webhook_dead_letter[each.value.servicio].id
    max_delivery_attempts = 5
  }

  depends_on = [
    google_pubsub_topic.webhook_topic,
    google_pubsub_topic.webhook_dead_letter,
  ]
}

# Permiso para que Pub/Sub publique en el dead-letter topic
resource "google_pubsub_topic_iam_member" "pubsub_dead_letter_publisher" {
  for_each = toset(local.webhook_services)
  project  = local.project
  topic    = google_pubsub_topic.webhook_dead_letter[each.value].name
  role     = "roles/pubsub.publisher"
  member   = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"

  depends_on = [google_pubsub_topic.webhook_dead_letter]
}

# ══════════════════════════════════════════════════════════════════════════════
# Cloud Function Gen2 — webhook-router
# Fuente: webhooks/router/
# Almacenada en GCS antes del deploy (ver Makefile)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_storage_bucket" "webhook_source" {
  name                        = "${local.project}-webhook-source"
  location                    = local.region
  project                     = local.project
  uniform_bucket_level_access = true
  labels                      = local.labels

  # Limpia versiones antiguas automáticamente
  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 30 }
  }

  depends_on = [google_project_service.webhook_apis]
}

resource "google_storage_bucket_object" "webhook_router_source" {
  name   = "webhook-router-${var.webhook_router_source_hash}.zip"
  bucket = google_storage_bucket.webhook_source.name
  source = var.webhook_router_source_zip # path local al zip del source
}

resource "google_cloudfunctions2_function" "webhook_router" {
  name     = "webhook-router"
  location = local.region
  project  = local.project
  labels   = local.labels

  description = "Router universal de webhooks — valida firma, despacha a Pub/Sub"

  build_config {
    runtime     = "python312"
    entry_point = "webhook_router"

    source {
      storage_source {
        bucket = google_storage_bucket.webhook_source.name
        object = google_storage_bucket_object.webhook_router_source.name
      }
    }
  }

  service_config {
    min_instance_count             = var.webhook_router_min_instances
    max_instance_count             = var.webhook_router_max_instances
    available_memory               = "256M"
    timeout_seconds                = 30
    service_account_email          = google_service_account.webhook_router_sa.email
    ingress_settings               = "ALLOW_ALL" 
    all_traffic_on_latest_revision = true

    environment_variables = {
      GOOGLE_CLOUD_PROJECT = local.project
    }
  }

  depends_on = [
    google_project_service.webhook_apis,
    google_storage_bucket_object.webhook_router_source,
    google_project_iam_member.router_pubsub_publisher,
    google_project_iam_member.router_secret_accessor,
  ]
}

# Solo el API Gateway puede invocar la CF (no-allow-unauthenticated)
resource "google_cloud_run_service_iam_member" "gateway_can_invoke_router" {
  project  = local.project
  location = local.region
  service  = google_cloudfunctions2_function.webhook_router.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.webhook_gateway_sa.email}"
}

resource "google_service_account_iam_member" "apigateway_can_impersonate_gateway_sa" {
  service_account_id = google_service_account.webhook_gateway_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${var.project_number}@gcp-sa-apigateway.iam.gserviceaccount.com"
}

# ══════════════════════════════════════════════════════════════════════════════
# API Gateway — hiluca-webhook-gateway
# OpenAPI spec en: webhooks/gateway/api-config.yaml
# ══════════════════════════════════════════════════════════════════════════════

resource "google_api_gateway_api" "webhook_api" {
  provider = google-beta
  api_id   = "hiluca-webhook-gateway"
  project  = local.project

  display_name = "HiLuca Webhook Gateway"

  depends_on = [google_project_service.webhook_apis]
}

resource "google_api_gateway_api_config" "webhook_api_config" {
  provider      = google-beta
  api           = google_api_gateway_api.webhook_api.api_id
  api_config_id = "webhook-gateway-config-${var.gateway_config_version}"
  project       = local.project

  display_name = "Webhook Gateway Config v${var.gateway_config_version}"

  openapi_documents {
    document {
      path = "api-config.yaml"
      # El content es el OpenAPI spec ya con la URL de la CF reemplazada
      contents = base64encode(
        replace(
          file(var.gateway_openapi_spec_path),
          "<ROUTER_CF_URL>",
          google_cloudfunctions2_function.webhook_router.service_config[0].uri
        )
      )
    }
  }

  gateway_config {
    backend_config {
      google_service_account = google_service_account.webhook_gateway_sa.email
    }
  }

  lifecycle {
    # Requiere nuevo api_config_id para cada actualización del spec.
    # Incrementa gateway_config_version en las variables.
    create_before_destroy = true
  }

  depends_on = [
    google_api_gateway_api.webhook_api,
    google_cloudfunctions2_function.webhook_router,
  ]
}

resource "google_api_gateway_gateway" "webhook_gateway" {
  provider   = google-beta
  api_config = google_api_gateway_api_config.webhook_api_config.id
  gateway_id = "webhook-gateway"
  project    = local.project
  region     = local.region

  display_name = "HiLuca Webhook Gateway"

  depends_on = [google_api_gateway_api_config.webhook_api_config]
}
