# ══════════════════════════════════════════════════════════════════════════════
# main.tf – ADK Multi-Agent Service (Google Ads + Gemini)
#
# Despliega el servicio ADK como Cloud Run con acceso EXCLUSIVAMENTE por VPN.
# Ningún tráfico público puede llegar al servicio.
#
# Arquitectura de red:
#   [Cliente VPN] ──► [OpenVPN server] ──► [default VPC peering]
#                                                  │
#                                    [Serverless VPC Connector]
#                                                  │
#                                      [Cloud Run - ingress=internal]
#                                          │ (port 8000 - adk web)
# ══════════════════════════════════════════════════════════════════════════════

locals {
  prefix  = "hiluca-adk-${var.environment}"
  project = var.project_id
  region  = var.region

  image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/adk:${var.image_tag}"

  labels = {
    app         = "hiluca-adk"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# APIs requeridas
# ══════════════════════════════════════════════════════════════════════════════

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "vpcaccess.googleapis.com",
    "artifactregistry.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "aiplatform.googleapis.com",       # Vertex AI / Gemini via SA (ADC)
  ])

  project            = local.project
  service            = each.value
  disable_on_destroy = false
}

# ══════════════════════════════════════════════════════════════════════════════
# Service Account – mínimos privilegios necesarios
# ══════════════════════════════════════════════════════════════════════════════

resource "google_service_account" "adk_sa" {
  account_id   = "${local.prefix}-sa"
  display_name = "HiLuca ADK [${upper(var.environment)}] – Cloud Run SA"
  project      = local.project
  depends_on   = [google_project_service.apis]
}

# Leer secretos de Secret Manager
resource "google_project_iam_member" "adk_secret_accessor" {
  project = local.project
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.adk_sa.email}"
}

# Escribir logs a Cloud Logging
resource "google_project_iam_member" "adk_log_writer" {
  project = local.project
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.adk_sa.email}"
}

# Enviar métricas a Cloud Monitoring
resource "google_project_iam_member" "adk_metric_writer" {
  project = local.project
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.adk_sa.email}"
}

# Leer imágenes de Artifact Registry
resource "google_project_iam_member" "adk_artifact_reader" {
  project = local.project
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.adk_sa.email}"
}

# Llamar a Vertex AI / Gemini con Application Default Credentials
# Reemplaza el uso de GOOGLE_API_KEY (AI Studio). El SA se autentica
# automáticamente vía ADC en Cloud Run – sin claves API.
resource "google_project_iam_member" "adk_vertex_user" {
  project = local.project
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.adk_sa.email}"
}

# ══════════════════════════════════════════════════════════════════════════════
# Secret Manager – un secreto por variable de entorno
#
# Para cargar los valores después del terraform apply:
#   echo -n "TU_VALOR" | gcloud secrets versions add adk-google-api-key --data-file=-
# ══════════════════════════════════════════════════════════════════════════════

locals {
  # Mapa de nombre de secreto → descripción legible
  # GOOGLE_API_KEY y GOOGLE_GENAI_USE_VERTEXAI eliminados:
  # Gemini se autentica vía Vertex AI usando el SA de Cloud Run (ADC).
  secrets = {
    (var.secret_serpapi_key)                 = "SERPAPI_KEY – Google Search via SerpAPI"
    (var.secret_newsapi_key)                 = "NEWSAPI_KEY – Industry news feed"
    (var.secret_google_ads_customer_id)      = "GOOGLE_ADS_CUSTOMER_ID – Client ad account"
    (var.secret_google_ads_login_customer_id)= "GOOGLE_ADS_LOGIN_CUSTOMER_ID – MCC account"
    (var.secret_google_ads_developer_token)  = "GOOGLE_ADS_DEVELOPER_TOKEN – API access token"
    (var.secret_google_ads_client_id)        = "GOOGLE_ADS_CLIENT_ID – OAuth client"
    (var.secret_google_ads_client_secret)    = "GOOGLE_ADS_CLIENT_SECRET – OAuth secret"
    (var.secret_google_ads_refresh_token)    = "GOOGLE_ADS_REFRESH_TOKEN – OAuth refresh token"
  }
}

resource "google_secret_manager_secret" "adk_secrets" {
  for_each  = local.secrets
  secret_id = each.key
  project   = local.project

  labels = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# ══════════════════════════════════════════════════════════════════════════════
# Serverless VPC Connector
#
# Permite que Cloud Run (que vive en la infraestructura de Google) se conecte
# al default VPC, donde el peering con el servidor OpenVPN ya está activo.
#
# El conector usa una subred /28 dedicada – debe estar libre de conflictos.
# Default: 10.8.1.0/28 (justo después del pool VPN 10.8.0.0/24)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_vpc_access_connector" "adk_connector" {
  name          = "${local.prefix}-connector"
  region        = local.region
  project       = local.project
  network       = var.vpc_network
  ip_cidr_range = var.vpc_connector_subnet_cidr

  min_instances = 2
  max_instances = 3
  machine_type  = "e2-micro"

  depends_on = [google_project_service.apis]
}

# ══════════════════════════════════════════════════════════════════════════════
# Firewall Rule – permite tráfico del pool VPN al conector VPC
#
# Sin esta regla, los clientes VPN (10.8.0.0/24) no pueden alcanzar el
# Serverless VPC Connector ni las instancias de Cloud Run.
# ══════════════════════════════════════════════════════════════════════════════

resource "google_compute_firewall" "allow_vpn_to_adk" {
  name        = "${local.prefix}-allow-vpn"
  network     = var.vpc_network
  project     = local.project
  description = "[${upper(var.environment)}] Permite clientes VPN (${var.vpn_pool_cidr}) → ADK Cloud Run vía VPC Connector"

  allow {
    protocol = "tcp"
    ports    = ["8000", "443", "80"]
  }

  # Solo tráfico originado desde el pool de clientes OpenVPN
  source_ranges = [var.vpn_pool_cidr]

  # También permite el tráfico desde el servidor VPN mismo (necesario para el peering de red)
  # El rango del servidor OpenVPN vive en la subred del VPC Connector
  # y también en la VPC peered (10.10.0.0/24 según openvpn/main.tf)
  # Incluimos ambos para no romper el peering existente.
  # Nota: el tag target se omite para aplicar a todas las instancias del VPC incluyendo el connector.

  depends_on = [google_project_service.apis]
}

# ══════════════════════════════════════════════════════════════════════════════
# Cloud Run Service – ADK Web UI
#
# SEGURIDAD CLAVE:
#   ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"
#   → Rechaza CUALQUIER request que no venga del VPC interno.
#   → Ningún cliente de internet puede llegar al servicio, ni con la URL directa.
# ══════════════════════════════════════════════════════════════════════════════

resource "google_cloud_run_v2_service" "adk" {
  name     = local.prefix
  location = local.region
  project  = local.project

  labels = local.labels

  # ── CONTROL DE ACCESO DE RED ───────────────────────────────────────────────
  # INTERNAL_ONLY: solo tráfico desde el VPC (y por tanto solo desde la VPN)
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.adk_sa.email

    labels = local.labels

    # ── VPC Connector: enruta el tráfico del servicio por el VPC interno ──────
    vpc_access {
      connector = google_vpc_access_connector.adk_connector.id
      egress    = "ALL_TRAFFIC"
    }

    # ── Recursos por instancia ────────────────────────────────────────────────
    containers {
      image = local.image
      name  = "adk"

      ports {
        container_port = 8000
        name           = "http1"
      }

      resources {
        limits = {
          memory = var.cloud_run_memory
          cpu    = var.cloud_run_cpu
        }
        # startup_cpu_boost: da más CPU durante el cold start (mejora latencia inicial)
        cpu_idle          = false
        startup_cpu_boost = true
      }

      # ── Variables de entorno inyectadas desde Secret Manager ───────────────
      # Gemini / Vertex AI: autenticado vía Application Default Credentials (ADC).
      # El SA del servicio (adk_sa) tiene roles/aiplatform.user — no se necesita API key.

      # Activa el backend Vertex AI en el ADK (en lugar de AI Studio con API key)
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "TRUE"
      }

      # Proyecto GCP para Vertex AI
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = local.project
      }

      # Región de Vertex AI (debe coincidir con la región de Cloud Run)
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = local.region
      }

      env {
        name = "SERPAPI_KEY"
        value_source {
          secret_key_ref {
            secret  = var.secret_serpapi_key
            version = "latest"
          }
        }
      }

      env {
        name = "NEWSAPI_KEY"
        value_source {
          secret_key_ref {
            secret  = var.secret_newsapi_key
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_ADS_CUSTOMER_ID"
        value_source {
          secret_key_ref {
            secret  = var.secret_google_ads_customer_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_ADS_LOGIN_CUSTOMER_ID"
        value_source {
          secret_key_ref {
            secret  = var.secret_google_ads_login_customer_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_ADS_DEVELOPER_TOKEN"
        value_source {
          secret_key_ref {
            secret  = var.secret_google_ads_developer_token
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_ADS_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = var.secret_google_ads_client_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_ADS_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = var.secret_google_ads_client_secret
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_ADS_REFRESH_TOKEN"
        value_source {
          secret_key_ref {
            secret  = var.secret_google_ads_refresh_token
            version = "latest"
          }
        }
      }

      # Startup probe: espera hasta 3 min para que ADK cargue todos los agentes
      startup_probe {
        http_get {
          path = "/"
          port = 8000
        }
        initial_delay_seconds = 15
        period_seconds        = 10
        failure_threshold     = 18  # 18 * 10s = 3 min
        timeout_seconds       = 5
      }

      # Liveness probe: Cloud Run reinicia la instancia si falla
      liveness_probe {
        http_get {
          path = "/"
          port = 8000
        }
        period_seconds    = 30
        failure_threshold = 3
        timeout_seconds   = 5
      }
    }

    # ── Escalado ───────────────────────────────────────────────────────────────
    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    # Timeout extendido para sesiones SSE largas (máximo permitido: 3600s)
    timeout = "3600s"

    # Máximo de solicitudes concurrentes por instancia
    # ADK es single-user por diseño – 1 sessión activa a la vez por instancia
    max_instance_request_concurrency = 5
  }

  depends_on = [
    google_project_service.apis,
    google_vpc_access_connector.adk_connector,
    google_service_account.adk_sa,
    google_secret_manager_secret.adk_secrets,
    google_project_iam_member.adk_secret_accessor,
  ]
}

# ══════════════════════════════════════════════════════════════════════════════
# Cloud Run IAM – SIN invoker público
#
# NO se añade allUsers ni allAuthenticatedUsers.
# Solo usuarios autenticados con VPN + Google Account pueden invocar el servicio.
# Cloud Run con ingress=INTERNAL_ONLY ya bloquea a nivel de red;
# esto añade una segunda capa de control de identidad.
# ══════════════════════════════════════════════════════════════════════════════

# NOTA: El servicio tiene ingress=INTERNAL_ONLY. Para que un usuario lo acceda
# desde el browser vía VPN, necesita ser miembro authorizado.
# Aggrega cada miembro del equipo con:
#
#   gcloud run services add-iam-policy-binding hiluca-adk-dev \
#     --region=us-central1 \
#     --member="user:victor@hiluca.com" \
#     --role="roles/run.invoker"
#
# O usa un grupo de Google Workspace para todo el equipo:
#   --member="group:equipo@hiluca.com"
#
# El service account del servicio se autentica a sí mismo para health checks internos:
resource "google_cloud_run_v2_service_iam_member" "adk_sa_invoker" {
  project  = local.project
  location = local.region
  name     = google_cloud_run_v2_service.adk.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.adk_sa.email}"
}

# ── Acceso desde el servidor OpenVPN (reverse proxy) ──────────────────────────
#
# allUsers está bloqueado por la org policy de GCP.
# En su lugar, el nginx del servidor VPN se autentica usando el identity token
# de su propio Service Account (compute SA por defecto).
#
# Para otorgar acceso, ejecuta una vez desde tu Mac:
#
#   SA=$(gcloud compute instances describe vpn-network-vpn \
#         --zone=us-central1-a \
#         --format='value(serviceAccounts[0].email)')
#
#   gcloud run services add-iam-policy-binding hiluca-adk-dev \
#     --region=us-central1 \
#     --member="serviceAccount:$SA" \
#     --role="roles/run.invoker"
#
# El nginx en el servidor VPN agrega el Bearer token en cada request
# mediante un cron que refresca el token cada 45 min (tokens duran 1h).
