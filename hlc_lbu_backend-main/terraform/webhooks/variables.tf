# ══════════════════════════════════════════════════════════════════════════════
# variables.tf – HiLuca Webhook Gateway Infrastructure
# ══════════════════════════════════════════════════════════════════════════════

# ── Proyecto GCP ──────────────────────────────────────────────────────────────

variable "project_id" {
  type        = string
  description = "ID del proyecto GCP. Ej: careful-acumen-422922-k4"
}

variable "project_number" {
  type        = string
  description = "Número del proyecto GCP. Requerido para el SA de Pub/Sub dead-letter. Ej: 401654669410"
}

variable "region" {
  type        = string
  description = "Región principal de GCP."
  default     = "us-central1"
}

# ── Servicios de Webhook ───────────────────────────────────────────────────────

variable "webhook_services" {
  type        = list(string)
  description = <<-EOT
    Lista de servicios de webhook registrados.
    Por cada servicio se crean:
      - Secret Manager: wh-secret-{servicio}
      - Pub/Sub topics: wh-{servicio}-dev  y  wh-{servicio}-prd
      - Dead-letter topic: wh-{servicio}-dead-letter
      - Subscription: wh-sub-{servicio}-{entorno}
    Agregar el slug aquí cuando se registre un nuevo proveedor en registry.py.
  EOT
  default     = ["appsflyer"]

  validation {
    condition     = length(var.webhook_services) > 0
    error_message = "Debe existir al menos un servicio de webhook."
  }
}

# ── Cloud Function webhook-router ──────────────────────────────────────────────

variable "webhook_router_source_zip" {
  type        = string
  description = <<-EOT
    Path local al archivo ZIP con el source de la CF webhook-router.
    Se genera con: make zip-router   (desde la raíz del repo)
    Ej: ../../webhooks/router/source.zip
  EOT
}

variable "webhook_router_source_hash" {
  type        = string
  description = <<-EOT
    Hash MD5 del ZIP de source (para forzar re-deploy cuando cambia el código).
    Se genera con: md5 -q webhooks/router/source.zip
    Ej: a1b2c3d4e5f6...
  EOT
}

variable "webhook_router_min_instances" {
  type        = number
  description = "Instancias mínimas de la CF webhook-router. 0 en dev para ahorrar costos."
  default     = 0
}

variable "webhook_router_max_instances" {
  type        = number
  description = "Instancias máximas de la CF webhook-router."
  default     = 10
}

# ── API Gateway ────────────────────────────────────────────────────────────────

variable "gateway_openapi_spec_path" {
  type        = string
  description = <<-EOT
    Path local al archivo api-config.yaml del gateway.
    Ej: ../../webhooks/gateway/api-config.yaml
    Terraform reemplaza automáticamente <ROUTER_CF_URL> con la URL real de la CF.
  EOT
  default     = "../../webhooks/gateway/api-config.yaml"
}

variable "gateway_config_version" {
  type        = string
  description = <<-EOT
    Versión de la configuración del API Gateway.
    Incrementar con cada cambio al OpenAPI spec para crear una nueva config.
    API Gateway requiere un nuevo resource para cada actualización del spec.
    Ej: "v1", "v2", "v3"
  EOT
  default     = "v1"
}
