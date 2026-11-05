# ══════════════════════════════════════════════════════════════════════════════
# variables.tf – HiLuca LBU Infrastructure (Multi-Environment)
# ══════════════════════════════════════════════════════════════════════════════

# ── Ambiente ──────────────────────────────────────────────────────────────────

variable "environment" {
  type        = string
  description = "Ambiente de despliegue. Afecta nombres de recursos, tamaños y configuraciones."

  validation {
    condition     = contains(["dev", "qas", "prd"], var.environment)
    error_message = "El ambiente debe ser: dev | qas | prd."
  }
}

# ── Proyecto GCP ──────────────────────────────────────────────────────────────

variable "project_id" {
  type        = string
  description = "ID del proyecto GCP donde se desplegará la infraestructura."
}

variable "region" {
  type        = string
  description = "Región principal de GCP."
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "Zona de GCP para la Compute Engine instance."
  default     = "us-central1-a"
}

# ── Compute Engine ────────────────────────────────────────────────────────────

variable "vm_machine_type" {
  type        = string
  description = "Tipo de máquina para la VM."
  # dev=e2-micro, qas=e2-standard-2, prd=e2-standard-2
}

variable "vm_disk_size_gb" {
  type        = number
  description = "Tamaño del disco de arranque en GB."
}

variable "gh_actions_ssh_public_key" {
  type        = string
  description = "Llave pública SSH para GitHub Actions. Genera con: ssh-keygen -t ed25519 -C 'github-actions@hiluca'"
  sensitive   = false
}

# ── Cloud SQL ─────────────────────────────────────────────────────────────────

variable "db_tier" {
  type        = string
  description = "Tier de Cloud SQL. dev=db-f1-micro, qas=db-g1-small, prd=db-g1-small o superior."
}

variable "db_name_strapi" {
  type        = string
  description = "Nombre de la DB para Strapi."
  default     = "strapi"
}

variable "db_name_sinergia" {
  type        = string
  description = "Nombre de la DB para Sinergia."
  default     = "sinergia"
}

variable "db_name_fury" {
  type        = string
  description = "Nombre de la DB para fury-langfuse."
  default     = "fury-langfuse"
}

variable "db_user_postgres" {
  type        = string
  description = "Usuario postgres de Cloud SQL."
  default     = "postgres"
}

variable "db_password_postgres" {
  type        = string
  description = "Contraseña del usuario postgres de Cloud SQL."
  sensitive   = true
}

variable "db_user" {
  type        = string
  description = "Usuario de Cloud SQL."
  default     = "hiluca"
}

variable "db_password" {
  type        = string
  description = "Contraseña del usuario de Cloud SQL."
  sensitive   = true
}

variable "db_reader_password" {
  type        = string
  description = "Contraseña para los usuarios *_reader (rol hiluca_readonly). Generada y almacenada de forma segura."
  sensitive   = true
}

variable "db_writer_password" {
  type        = string
  description = "Contraseña para los usuarios *_writer (rol hiluca_readwrite). Generada y almacenada de forma segura."
  sensitive   = true
}

variable "db_enable_backups" {
  type        = bool
  description = "Habilitar backups automáticos en Cloud SQL. Recomendado: false en dev, true en qas/prd."
  default     = true
}

variable "db_deletion_protection" {
  type        = bool
  description = "Proteger la instancia Cloud SQL contra borrado accidental. Siempre true en prd."
  default     = false
}

variable "db_disk_size_gb" {
  type        = number
  description = "Tamaño inicial del disco de Cloud SQL en GB."
  default     = 20
}

# ── Load Balancer / SSL ───────────────────────────────────────────────────────

variable "domain" {
  type        = string
  description = "Dominio completo para el certificado SSL gestionado por Google. Ej: dev.hiluca.com"
}

variable "health_check_path" {
  type        = string
  description = "Path del health check del Load Balancer."
  default     = "/health"
}

# ── Artifact Registry ─────────────────────────────────────────────────────────

variable "artifact_registry_repo" {
  type        = string
  description = "Nombre del repositorio de Artifact Registry."
  default     = "hiluca-docker-repository"
}

# ── Secret Manager ────────────────────────────────────────────────────────────

variable "env_secret_name" {
  type        = string
  description = "Nombre del secret en Secret Manager con el .env del ambiente. Ej: hiluca-lbu-prd-env"
}

# ── Cloud Armor ───────────────────────────────────────────────────────────────

variable "enable_cloud_armor" {
  type        = bool
  description = "Habilitar Cloud Armor WAF (SQLi, XSS, LFI, RFI). Costo: ~$5/mes. false en dev, true en qas/prd."
  default     = false
}

# ── Monitoring ────────────────────────────────────────────────────────────────

variable "alert_email" {
  type        = string
  description = "Email para alertas de uptime y latencia. Dejar '' para deshabilitar."
  default     = ""
}

# ── SSL Certificate (Secret Manager) ─────────────────────────────────────────
# Los certificados se guardan en Secret Manager (no en archivos locales).
# Para subir tu cert:
#   gcloud secrets create hiluca-lbu-ssl-cert --data-file="sec.hiluca.com.crt"
#   gcloud secrets create hiluca-lbu-ssl-key  --data-file="sec.hiluca.com.key"
# Para renovar (nueva versión):
#   gcloud secrets versions add hiluca-lbu-ssl-cert --data-file="sec.hiluca.com.crt"
#   terraform apply  ← recrea el google_compute_ssl_certificate automáticamente

variable "ssl_cert_secret_name" {
  type        = string
  description = "Nombre del secret en Secret Manager con el certificado SSL (PEM completo, incluye intermediarios). Ej: hiluca-lbu-ssl-cert"
}

variable "ssl_key_secret_name" {
  type        = string
  description = "Nombre del secret en Secret Manager con la llave privada SSL (PEM). Ej: hiluca-lbu-ssl-key"
}

