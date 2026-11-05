# ══════════════════════════════════════════════════════════════════════════════
# variables.tf – ADK Multi-Agent Service
# ══════════════════════════════════════════════════════════════════════════════

# ── Proyecto GCP ──────────────────────────────────────────────────────────────

variable "project_id" {
  type        = string
  description = "ID del proyecto GCP donde se desplegará el servicio ADK."
}

variable "region" {
  type        = string
  description = "Región principal de GCP para Cloud Run y el VPC Connector."
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Ambiente de despliegue. Afecta nombres de recursos y config (dev | prd)."

  validation {
    condition     = contains(["dev", "prd"], var.environment)
    error_message = "El ambiente debe ser: dev | prd."
  }
}

# ── Artifact Registry ─────────────────────────────────────────────────────────

variable "artifact_registry_repo" {
  type        = string
  description = "Nombre del repositorio de Artifact Registry donde vive la imagen ADK."
  default     = "hiluca-docker-repository"
}

variable "image_tag" {
  type        = string
  description = "Tag de la imagen Docker a desplegar. Usa 'dev' o 'prd' para seguir la convención del proyecto."
  default     = "dev"
}

# ── Network ───────────────────────────────────────────────────────────────────

variable "vpc_network" {
  type        = string
  description = "Nombre del VPC donde existe el peering de OpenVPN. Generalmente 'default'."
  default     = "default"
}

variable "vpc_connector_subnet_cidr" {
  type        = string
  description = "CIDR /28 para el Serverless VPC Connector. Debe ser un rango libre dentro del VPC."
  default     = "10.8.1.0/28"
}

variable "vpn_pool_cidr" {
  type        = string
  description = "CIDR del pool de IPs del cliente OpenVPN. Los clientes conectados a la VPN tendrán IPs de este rango."
  default     = "10.8.0.0/24"
}

# ── Secret Manager – nombres de secretos ──────────────────────────────────────
# Los valores reales se cargan con:
#   gcloud secrets versions add <secret_name> --data-file=<file>
# o directamente:
#   echo -n "valor" | gcloud secrets versions add <secret_name> --data-file=-

variable "secret_google_api_key" {
  type        = string
  description = "Nombre del secreto en Secret Manager para GOOGLE_API_KEY (Gemini)."
  default     = "adk-google-api-key"
}

variable "secret_google_genai_use_vertexai" {
  type        = string
  description = "Nombre del secreto en Secret Manager para GOOGLE_GENAI_USE_VERTEXAI."
  default     = "adk-google-genai-use-vertexai"
}

variable "secret_serpapi_key" {
  type        = string
  description = "Nombre del secreto en Secret Manager para SERPAPI_KEY."
  default     = "adk-serpapi-key"
}

variable "secret_newsapi_key" {
  type        = string
  description = "Nombre del secreto en Secret Manager para NEWSAPI_KEY."
  default     = "adk-newsapi-key"
}

variable "secret_google_ads_customer_id" {
  type        = string
  description = "Nombre del secreto en Secret Manager para GOOGLE_ADS_CUSTOMER_ID."
  default     = "adk-google-ads-customer-id"
}

variable "secret_google_ads_login_customer_id" {
  type        = string
  description = "Nombre del secreto en Secret Manager para GOOGLE_ADS_LOGIN_CUSTOMER_ID."
  default     = "adk-google-ads-login-customer-id"
}

variable "secret_google_ads_developer_token" {
  type        = string
  description = "Nombre del secreto en Secret Manager para GOOGLE_ADS_DEVELOPER_TOKEN."
  default     = "adk-google-ads-developer-token"
}

variable "secret_google_ads_client_id" {
  type        = string
  description = "Nombre del secreto en Secret Manager para GOOGLE_ADS_CLIENT_ID."
  default     = "adk-google-ads-client-id"
}

variable "secret_google_ads_client_secret" {
  type        = string
  description = "Nombre del secreto en Secret Manager para GOOGLE_ADS_CLIENT_SECRET."
  default     = "adk-google-ads-client-secret"
}

variable "secret_google_ads_refresh_token" {
  type        = string
  description = "Nombre del secreto en Secret Manager para GOOGLE_ADS_REFRESH_TOKEN."
  default     = "adk-google-ads-refresh-token"
}

# ── Cloud Run ─────────────────────────────────────────────────────────────────

variable "cloud_run_min_instances" {
  type        = number
  description = "Mínimo de instancias de Cloud Run. Usa 0 en dev (ahorra costos), 1 en prd (evita cold starts)."
  default     = 0
}

variable "cloud_run_max_instances" {
  type        = number
  description = "Máximo de instancias de Cloud Run."
  default     = 3
}

variable "cloud_run_memory" {
  type        = string
  description = "Memoria asignada por instancia de Cloud Run. ADK + Google Ads client necesita al menos 512Mi."
  default     = "1Gi"
}

variable "cloud_run_cpu" {
  type        = string
  description = "CPUs asignadas por instancia de Cloud Run."
  default     = "1"
}

# ── Monitoring ────────────────────────────────────────────────────────────────

variable "alert_email" {
  type        = string
  description = "Email para alertas de errores del servicio ADK. Deja '' para deshabilitar."
  default     = ""
}
