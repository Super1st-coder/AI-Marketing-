output "pubsub_topic_id" {
  description = "ID completo del Pub/Sub topic al que se publican las alertas de budget."
  value       = google_pubsub_topic.billing_alerts.id
}

output "pubsub_topic_name" {
  description = "Nombre del Pub/Sub topic."
  value       = google_pubsub_topic.billing_alerts.name
}

output "cloud_function_name" {
  description = "Nombre de la Cloud Function Gen 2 (HTTP/Scheduler)."
  value       = google_cloudfunctions2_function.billing_cap.name
}

output "cloud_function_uri" {
  description = "URI del servicio Cloud Run subyacente de la función HTTP."
  value       = google_cloudfunctions2_function.billing_cap.service_config[0].uri
}

output "cloud_function_pubsub_name" {
  description = "Nombre de la Cloud Function Gen 2 de redundancia Pub/Sub."
  value       = google_cloudfunctions2_function.billing_cap_pubsub.name
}

output "service_account_email" {
  description = "Email de la Service Account que ejecuta la Cloud Function."
  value       = google_service_account.billing_cap.email
}

output "budget_id" {
  description = "ID del Budget Alert creado en la billing account."
  value       = google_billing_budget.monthly_cap.id
}

output "function_source_bucket" {
  description = "Nombre del GCS bucket que contiene el ZIP del código fuente."
  value       = google_storage_bucket.function_source.name
}

output "protection_mode" {
  description = "Modo de protección activo: 'explicit' si se definieron proyectos, 'all-except-excluded' si no."
  value       = length(var.protected_project_ids) > 0 ? "explicit (${length(var.protected_project_ids)} proyectos)" : "all-except-excluded (${length(var.excluded_project_ids)} excluidos)"
}
