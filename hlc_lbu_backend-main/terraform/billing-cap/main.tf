# ══════════════════════════════════════════════════════════════════════════════
# Billing Cap – Cloud Function Gen 2 + Budget Alert + Pub/Sub
# ══════════════════════════════════════════════════════════════════════════════
# Arquitectura:
#   Budget Alert → Pub/Sub Topic → Cloud Function (Gen 2) → Disable Billing API
# ══════════════════════════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

provider "google" {
  project               = var.host_project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.host_project_id
}

locals {
  function_name   = "billing-cap"
  sa_account_id   = "billing-cap-sa"
  topic_name      = "billing-budget-alerts"
  bucket_name     = "${var.host_project_id}-billing-cap-src"
}

# Data source: obtiene el número de proyecto (requerido para el SA del Pub/Sub service agent)
data "google_project" "host" {
  project_id = var.host_project_id
}

# ── APIs requeridas ────────────────────────────────────────────────────────────

resource "google_project_service" "required_apis" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudbilling.googleapis.com",
    "storage.googleapis.com",
    "eventarc.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "monitoring.googleapis.com",
    "vpcaccess.googleapis.com",
  ])

  project            = var.host_project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_service_account" "billing_cap" {
  project      = var.host_project_id
  account_id   = local.sa_account_id
  display_name = "Billing Cap – Cloud Function SA"
  description  = "SA utilizado por la Cloud Function billing-cap para deshabilitar billing en proyectos protegidos."

  depends_on = [google_project_service.required_apis]
}

# NOTA: El rol roles/billing.admin para la SA fue otorgado manualmente
# por el administrador de la billing account desde GCP Console.
# SA: billing-cap-sa@careful-acumen-422922-k4.iam.gserviceaccount.com

# IAM: billing-cap-sa necesita leer métricas de Cloud Monitoring para obtener el gasto actual
resource "google_project_iam_member" "billing_cap_monitoring_viewer" {
  project = var.host_project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.billing_cap.email}"
}

# DESHABILITADO: Cloud Scheduler SA — solo se usa si se reactiva el scheduler como fallback.
# resource "google_service_account" "scheduler" {
#   project      = var.host_project_id
#   account_id   = "billing-cap-scheduler"
#   display_name = "Billing Cap – Cloud Scheduler SA"
#   description  = "SA utilizado por Cloud Scheduler para invocar la Cloud Function billing-cap via HTTP."
#   depends_on   = [google_project_service.required_apis]
# }

resource "google_pubsub_topic" "billing_alerts" {
  project = var.host_project_id
  name    = local.topic_name

  message_retention_duration = "604800s"

  depends_on = [google_project_service.required_apis]
}

# Espera de propagación: las APIs recién habilitadas necesitan ~30s para estar disponibles
resource "time_sleep" "api_propagation" {
  create_duration = "30s"
  depends_on      = [google_project_service.required_apis]
}

# ── Serverless VPC Access Connector ──────────────────────────────────────────
# Requerido por org policy constraints/run.allowedVPCEgress.
# Sin un connector (o network-interfaces), Cloud Run no permite establecer
# el annotation vpc-access-egress y el apply falla con HTTP 400.
# Usamos PRIVATE_RANGES_ONLY: solo tráfico RFC-1918 va por VPC;
# las llamadas a GCP APIs (billing, monitoring) continúan por internet.
resource "google_vpc_access_connector" "billing_cap" {
  project       = var.host_project_id
  name          = "billing-cap-vpc-conn"
  region        = var.region
  network       = "default"
  ip_cidr_range = "10.8.0.0/28"
  min_throughput = 200
  max_throughput = 300

  depends_on = [google_project_service.required_apis]
}


resource "google_billing_budget" "monthly_cap" {
  billing_account = var.billing_account_id
  # NOTA: La moneda DEBE coincidir con la de la billing account (MXN).
  display_name    = "Monthly Cap - ${var.budget_amount_mxn} MXN"

  budget_filter {
    # MODO 1: Proyectos explícitos. MODO 2: null → toda la billing account.
    projects               = length(var.protected_project_ids) > 0 ? [for pid in var.protected_project_ids : "projects/${pid}"] : null
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      # ¡IMPORTANTE! Debe ser MXN — la billing account está en pesos mexicanos.
      currency_code = "MXN"
      units         = tostring(var.budget_amount_mxn)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  # ── Threshold 80% – Alerta de advertencia ───────────────────────
  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }

  # ── Threshold 100% – Dispara Cloud Function → Deshabilita billing
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  # ── Threshold 110% proyectado – Alerta de pronóstico ────────────
  threshold_rules {
    threshold_percent = 1.1
    spend_basis       = "FORECASTED_SPEND"
  }

  # ── Pub/Sub Budget Alert ─────────────────────────────────────────────────────
  # La DRS org policy fue overrideada a nivel de proyecto con:
  #   gcloud org-policies reset constraints/iam.allowedPolicyMemberDomains \
  #     --project=careful-acumen-422922-k4
  # Esto permite que la Budget API otorgue IAM al topic internamente.
  all_updates_rule {
    pubsub_topic                     = google_pubsub_topic.billing_alerts.id
    schema_version                   = "1.0"
    monitoring_notification_channels = var.notification_channel_ids
  }

  lifecycle {
    ignore_changes = []
  }

  depends_on = [
    google_pubsub_topic.billing_alerts,
    time_sleep.api_propagation,
  ]
}


# ── GCS Bucket para el código fuente ─────────────────────────────────────────

resource "google_storage_bucket" "function_source" {
  project                     = var.host_project_id
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.required_apis]
}

# Empacar el código de la función en un ZIP (se actualiza si cambia el código)
data "archive_file" "billing_cap" {
  type        = "zip"
  source_dir  = "${path.module}/../../billing_cap"
  output_path = "${path.module}/billing_cap_source.zip"
}

resource "google_storage_bucket_object" "function_source" {
  name   = "billing_cap_${data.archive_file.billing_cap.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.billing_cap.output_path
}

# ── Cloud Function Gen 2 ──────────────────────────────────────────────────────

resource "google_cloudfunctions2_function" "billing_cap" {
  project  = var.host_project_id
  name     = local.function_name
  location = var.region
  description = "Deshabilita billing en proyectos protegidos cuando el presupuesto mensual es superado."

  build_config {
    runtime     = "python311"
    entry_point = "check_billing_scheduler"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.function_source.name
      }
    }
  }

  service_config {
    max_instance_count    = 3
    min_instance_count    = 0
    available_memory      = "256Mi"
    timeout_seconds       = 120
    # ALLOW_ALL: Cloud Scheduler invoca via HTTP con OIDC token.
    # La protección es por IAM (roles/run.invoker en el scheduler SA).
    ingress_settings      = "ALLOW_ALL"
    # Requerido por org policy constraints/run.allowedVPCEgress.
    # PRIVATE_RANGES_ONLY: solo RFC-1918 va por VPC; GCP APIs siguen por internet.
    vpc_connector                 = google_vpc_access_connector.billing_cap.id
    vpc_connector_egress_settings = "PRIVATE_RANGES_ONLY"
    service_account_email         = google_service_account.billing_cap.email

    environment_variables = {
      # Proyecto host (requerido para consultar Cloud Monitoring)
      PROJECT_ID = var.host_project_id

      # MODO 1: Lista explícita (tiene prioridad si no está vacía)
      PROJECT_IDS = join(",", var.protected_project_ids)

      # MODO 2: Todos excepto excluidos
      BILLING_ACCOUNT_ID   = var.billing_account_id
      EXCLUDED_PROJECT_IDS = join(",", var.excluded_project_ids)

      # Guardia de periodo (ISO: YYYY-MM-DD)
      ACTIVE_FROM = var.active_from

      BUDGET_AMOUNT = tostring(var.budget_amount_mxn)
      LOG_LEVEL     = var.log_level
    }
  }

  # Sin event_trigger: función HTTP-only invocada por Cloud Scheduler.
  # La redundancia Pub/Sub la maneja billing-cap-pubsub (ver abajo).

  depends_on = [
    google_project_service.required_apis,
  ]
}

# ── Cloud Function Gen 2: trigger Pub/Sub (redundancia) ───────────────────────
# Segunda función para el entry point stop_billing, disparada por Budget Alert
# vía Pub/Sub. Actúa como capa de redundancia instantánea cuando el presupuesto
# supera el 100% (CURRENT_SPEND). El Scheduler sigue activo como polling proactivo.

resource "google_cloudfunctions2_function" "billing_cap_pubsub" {
  project     = var.host_project_id
  name        = "billing-cap-pubsub"
  location    = var.region
  description = "Redundancia Pub/Sub: deshabilita billing al recibir alerta del Budget Alert (>= 100%)."

  build_config {
    runtime     = "python311"
    entry_point = "stop_billing"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.function_source.name
      }
    }
  }

  service_config {
    max_instance_count    = 3
    min_instance_count    = 0
    available_memory      = "256Mi"
    timeout_seconds       = 120
    ingress_settings      = "ALLOW_INTERNAL_ONLY"
    # Requerido por org policy constraints/run.allowedVPCEgress.
    # PRIVATE_RANGES_ONLY: solo RFC-1918 va por VPC; GCP APIs siguen por internet.
    vpc_connector                 = google_vpc_access_connector.billing_cap.id
    vpc_connector_egress_settings = "PRIVATE_RANGES_ONLY"
    service_account_email         = google_service_account.billing_cap.email

    environment_variables = {
      PROJECT_ID           = var.host_project_id
      PROJECT_IDS          = join(",", var.protected_project_ids)
      BILLING_ACCOUNT_ID   = var.billing_account_id
      EXCLUDED_PROJECT_IDS = join(",", var.excluded_project_ids)
      ACTIVE_FROM          = var.active_from
      BUDGET_AMOUNT        = tostring(var.budget_amount_mxn)
      LOG_LEVEL            = var.log_level
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic          = google_pubsub_topic.billing_alerts.id
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.billing_cap.email
  }

  depends_on = [
    google_project_service.required_apis,
    google_storage_bucket_object.function_source,
  ]
}

# ── IAM: Permitir que Cloud Scheduler invoque la Cloud Function (HTTP + OIDC) ─

resource "google_cloud_run_service_iam_member" "invoker" {
  project  = var.host_project_id
  location = var.region
  service  = google_cloudfunctions2_function.billing_cap.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.billing_cap.email}"
}

# DESHABILITADO: scheduler_invoker — re-habilitar junto con el scheduler job si se usa como fallback.
# resource "google_cloud_run_service_iam_member" "scheduler_invoker" {
#   project  = var.host_project_id
#   location = var.region
#   service  = google_cloudfunctions2_function.billing_cap.name
#   role     = "roles/run.invoker"
#   member   = "serviceAccount:${google_service_account.scheduler.email}"
# }

# IAM: billing-cap-sa invoca billing-cap-pubsub vía Eventarc (trigger Pub/Sub)
resource "google_cloud_run_service_iam_member" "pubsub_invoker" {
  project  = var.host_project_id
  location = var.region
  service  = google_cloudfunctions2_function.billing_cap_pubsub.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.billing_cap.email}"
}

# IAM: Cloud Run Service Agent necesita leer imágenes del Artifact Registry
# El SA service-{project_number}@serverless-robot-prod.iam.gserviceaccount.com es gestionado
# por Google y es el que jalará la imagen del contenedor en runtime. Sin este permiso,
# el despliegue falla con "must have permission to read the image".
resource "google_project_iam_member" "cloud_run_sa_artifact_reader" {
  project = var.host_project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:service-${data.google_project.host.number}@serverless-robot-prod.iam.gserviceaccount.com"

  depends_on = [google_project_service.required_apis]
}

# IAM: El Pub/Sub service agent necesita crear tokens OIDC como billing-cap-sa
# para que Eventarc pueda autenticar las invocaciones del trigger Pub/Sub.
# Requerido por Cloud Functions Gen 2 + Eventarc + Pub/Sub.
resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.billing_cap.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.host.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# DESHABILITADO: Cloud Scheduler — el trigger tiempo real es Budget → Pub/Sub → billing-cap-pubsub.
# Descomentar como fallback si se necesita polling complementario.
# resource "google_cloud_scheduler_job" "billing_cap_hourly" {
#   project     = var.host_project_id
#   region      = var.region
#   name        = "billing-cap-check"
#   description = "Verifica el gasto mensual contra el presupuesto cada 5 min y deshabilita billing si supera el límite."
#   schedule    = "*/5 * * * *"
#   time_zone   = "America/Mexico_City"
#
#   http_target {
#     http_method = "POST"
#     uri         = google_cloudfunctions2_function.billing_cap.service_config[0].uri
#
#     oidc_token {
#       service_account_email = google_service_account.scheduler.email
#       audience              = google_cloudfunctions2_function.billing_cap.service_config[0].uri
#     }
#   }
#
#   depends_on = [google_project_service.required_apis]
# }
