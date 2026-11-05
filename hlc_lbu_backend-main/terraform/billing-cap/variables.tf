# ══════════════════════════════════════════════════════════════════════════════
# Variables – Billing Cap Cloud Function
# ══════════════════════════════════════════════════════════════════════════════

variable "host_project_id" {
  type        = string
  description = "Project ID de GCP donde se desplegará la Cloud Function y el Pub/Sub topic."

  validation {
    condition     = length(var.host_project_id) > 4
    error_message = "El host_project_id debe ser un Project ID válido de GCP."
  }
}

variable "billing_account_id" {
  type        = string
  description = "ID de la Billing Account de GCP. Formato: XXXXXX-XXXXXX-XXXXXX"

  validation {
    condition     = can(regex("^[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$", var.billing_account_id))
    error_message = "El billing_account_id debe tener el formato XXXXXX-XXXXXX-XXXXXX."
  }
}

variable "region" {
  type        = string
  description = "Región de GCP donde se desplegará la Cloud Function y el bucket."
  default     = "us-central1"

  validation {
    condition = contains([
      "us-central1", "us-east1", "us-east4", "us-west1", "us-west2",
      "europe-west1", "europe-west2", "europe-west3", "europe-west6",
      "asia-east1", "asia-east2", "asia-northeast1", "northamerica-northeast1",
      "southamerica-east1",
    ], var.region)
    error_message = "La región especificada no es válida para Cloud Functions Gen 2."
  }
}

variable "budget_amount_mxn" {
  type        = number
  description = "Monto máximo mensual en MXN (pesos mexicanos). Al superarlo, se deshabilita el billing. La billing account usa MXN."
  default     = 30000

  validation {
    condition     = var.budget_amount_mxn > 0
    error_message = "El monto del presupuesto debe ser mayor a 0."
  }
}

# ── Modo de protección (elige UNO de los dos modos) ──────────────────────────
#
#   MODO 1: Especifica exactamente qué proyectos proteger.
#     protected_project_ids = ["proj-a", "proj-b"]
#
#   MODO 2: Protege TODOS los proyectos de la billing account
#           excepto los listados en excluded_project_ids.
#     protected_project_ids = []         (vacío → activa modo 2)
#     excluded_project_ids  = ["proj-exempt"]
#
# Si protected_project_ids tiene valores, tiene prioridad (modo 1).
# ─────────────────────────────────────────────────────────────────────────────

variable "protected_project_ids" {
  type        = list(string)
  description = <<-EOT
    MODO 1: Lista explícita de Project IDs cuyo billing se deshabilitará.
    Deja vacío ([]) para usar el MODO 2 (todos excepto las excepciones).
  EOT
  default     = []
}

variable "excluded_project_ids" {
  type        = list(string)
  description = <<-EOT
    MODO 2: Proyectos EXCLUIDOS de la desactivación de billing.
    La función protegerá TODOS los proyectos de la billing account
    EXCEPTO los listados aquí. Solo aplica cuando protected_project_ids = [].
    Ejemplo: proyectos de producción crítica que nunca deben pausarse.
  EOT
  default     = []
}

variable "notification_channel_ids" {
  type        = list(string)
  description = "IDs de Monitoring Notification Channels (email, Slack, PagerDuty) para recibir alertas de budget."
  default     = []
}

variable "log_level" {
  type        = string
  description = "Nivel de logging de la Cloud Function."
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "log_level debe ser uno de: DEBUG, INFO, WARNING, ERROR, CRITICAL."
  }
}

variable "active_from" {
  type        = string
  description = <<-EOT
    Fecha a partir de la cual la función está activa. Formato ISO: YYYY-MM-DD.
    Alertas de periodos de billing anteriores a esta fecha serán ignoradas.
    Útil para evitar que un mes ya excedido dispare el apagado al hacer el deploy.
    Ejemplo: "2026-04-01" para que solo actúe desde abril.
    Dejar vacío ("") para que actúe siempre.
  EOT
  default = ""

  validation {
    condition     = var.active_from == "" || can(regex("^\\d{4}-\\d{2}-\\d{2}$", var.active_from))
    error_message = "active_from debe estar vacío o tener el formato YYYY-MM-DD."
  }
}
