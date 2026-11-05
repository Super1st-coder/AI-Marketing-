# ══════════════════════════════════════════════════════════════════════════════
# outputs.tf – HiLuca Webhook Gateway Infrastructure
# ══════════════════════════════════════════════════════════════════════════════

output "webhook_router_url" {
  description = "URL de Cloud Function webhook-router. Ya está inyectada en el API Gateway."
  value       = google_cloudfunctions2_function.webhook_router.service_config[0].uri
}

output "webhook_gateway_url" {
  description = "URL pública del API Gateway. Apunta integrate.hiluca.com → esta URL."
  value       = "https://${google_api_gateway_gateway.webhook_gateway.default_hostname}"
}

output "webhook_router_sa_email" {
  description = "Email del Service Account del webhook-router."
  value       = google_service_account.webhook_router_sa.email
}

output "pubsub_topics" {
  description = "Map de topics Pub/Sub creados: wh-{servicio}-{entorno}"
  value = {
    for k, v in google_pubsub_topic.webhook_topic :
    k => v.name
  }
}

output "pubsub_dead_letter_topics" {
  description = "Map de dead-letter topics por servicio."
  value = {
    for k, v in google_pubsub_topic.webhook_dead_letter :
    k => v.name
  }
}

output "signing_secrets" {
  description = "Secrets de Secret Manager creados por servicio (solo la referencia, no el valor)."
  value = {
    for k, v in google_secret_manager_secret.webhook_signing_secret :
    k => v.secret_id
  }
}

output "next_steps" {
  description = "Pasos post-deploy del módulo webhooks."
  value       = <<-EOT

    ╔══════════════════════════════════════════════════════════════════════╗
    ║  ✅ WEBHOOK GATEWAY DESPLEGADO                                       ║
    ╠══════════════════════════════════════════════════════════════════════╣
    ║                                                                      ║
    ║  Gateway URL: https://${google_api_gateway_gateway.webhook_gateway.default_hostname}
    ║                                                                      ║
    ║  1. Sube el signing secret de AppsFlyer:                            ║
    ║     echo -n "TU_SECRET" | gcloud secrets versions add               ║
    ║       wh-secret-appsflyer --data-file=- --project=${var.project_id}
    ║                                                                      ║
    ║  2. Prueba el endpoint en dev (sin firma):                          ║
    ║     curl -X POST \                                                  ║
    ║       "https://${google_api_gateway_gateway.webhook_gateway.default_hostname}/webhook/appsflyer/v1.0.0/dev" \
    ║       -H "Content-Type: application/json" \                         ║
    ║       -d '{"appsflyer_id":"test-001","event_name":"install"}'       ║
    ║                                                                      ║
    ║  3. Apunta DNS:                                                     ║
    ║     integrate.hiluca.com → CNAME →                                 ║
    ║       ${google_api_gateway_gateway.webhook_gateway.default_hostname}
    ║                                                                      ║
    ║  4. Deploy CF procesadora de AppFlyer:                              ║
    ║     cd webhooks/appflyer/processor                                  ║
    ║     gcloud functions deploy wh-proc-appsflyer \                    ║
    ║       --gen2 --runtime python312 \                                  ║
    ║       --trigger-topic wh-appsflyer-prd ...                         ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝

  EOT
}
