# ══════════════════════════════════════════════════════════════════════════════
# outputs.tf – HiLuca LBU Infrastructure (Multi-Environment)
# ══════════════════════════════════════════════════════════════════════════════

output "environment" {
  description = "Ambiente desplegado."
  value       = var.environment
}

output "load_balancer_ip" {
  description = "IP global del LB. Apunta tu DNS → esta IP."
  value       = google_compute_global_address.lb_ip.address
}

output "vm_external_ip" {
  description = "IP externa de la VM (para SSH vía GitHub Actions)."
  value       = google_compute_instance.vm.network_interface[0].access_config[0].nat_ip
}

output "cloud_sql_connection_name" {
  description = "Connection name de Cloud SQL para el Auth Proxy."
  value       = google_sql_database_instance.postgres.connection_name
}

output "cloud_sql_public_ip" {
  description = "IP pública de Cloud SQL."
  value       = google_sql_database_instance.postgres.public_ip_address
}

output "vm_service_account_email" {
  description = "Email del Service Account de la VM."
  value       = google_service_account.vm_sa.email
}

output "secret_manager_secret_id" {
  description = "ID del secret del .env en Secret Manager."
  value       = google_secret_manager_secret.env_file.secret_id
}

output "artifact_registry_prefix" {
  description = "Prefijo del Artifact Registry para las imágenes."
  value       = local.ar_prefix
}

output "next_steps" {
  description = "Pasos post-deploy."
  value       = <<-EOT

    ╔══════════════════════════════════════════════════════════════════════╗
    ║  ✅ DEPLOY [${upper(var.environment)}] COMPLETADO
    ╠══════════════════════════════════════════════════════════════════════╣
    ║
    ║  1. DNS: Apunta ${var.domain} → ${google_compute_global_address.lb_ip.address}
    ║     (El cert SSL tardará ~15 min tras propagar el DNS)
    ║
    ║  2. Sube el .env de ${var.environment} a Secret Manager:
    ║     gcloud secrets versions add ${var.env_secret_name} \
    ║       --data-file=".env.${var.environment}" \
    ║       --project=${local.project}
    ║
    ║  3. Agrega en tu .env.${var.environment}:
    ║     CLOUD_SQL_CONNECTION_NAME=${google_sql_database_instance.postgres.connection_name}
    ║     AR_PREFIX=${local.ar_prefix}
    ║     DATABASE_HOST=cloud-sql-proxy
    ║     DATABASE_PORT=5432
    ║
    ║  4. GitHub Actions SSH:
    ║     Host: ${google_compute_instance.vm.network_interface[0].access_config[0].nat_ip}
    ║     User: ubuntu
    ║     Secret: VM_SSH_KEY_${upper(var.environment)}
    ║
    ╚══════════════════════════════════════════════════════════════════════╝

  EOT
}
