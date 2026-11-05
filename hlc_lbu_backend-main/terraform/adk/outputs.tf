# ══════════════════════════════════════════════════════════════════════════════
# outputs.tf – ADK Multi-Agent Service
# ══════════════════════════════════════════════════════════════════════════════

output "cloud_run_url" {
  description = <<-EOT
    URL interna del servicio ADK en Cloud Run.
    Solo accesible desde la red VPN. Abre esta URL en el browser
    mientras estás conectado al OpenVPN para acceder al ADK Web UI.
  EOT
  value       = google_cloud_run_v2_service.adk.uri
}

output "cloud_run_hostname" {
  description = <<-EOT
    Hostname del servicio ADK sin el prefijo https://.
    Úsalo como valor de adk_cloud_run_url en openvpn/terraform.tfvars
    para que nginx lo use como backend del reverse proxy.
    Ejemplo: hiluca-adk-dev-bvuoyah6iq-uc.a.run.app
  EOT
  value       = trimprefix(google_cloud_run_v2_service.adk.uri, "https://")
}

output "service_account_email" {
  description = "Email del Service Account que usa el servicio ADK."
  value       = google_service_account.adk_sa.email
}

output "vpc_connector_id" {
  description = "ID del Serverless VPC Connector que conecta Cloud Run al VPC."
  value       = google_vpc_access_connector.adk_connector.id
}

output "secret_names" {
  description = "Lista de secretos creados en Secret Manager. Carga los valores con 'gcloud secrets versions add'."
  value       = keys(google_secret_manager_secret.adk_secrets)
}

output "load_secrets_commands" {
  description = "Comandos de referencia para cargar los valores de los secretos en Secret Manager."
  value = <<-EOT
    # ── Carga los secretos con los valores reales ────────────────────────────
    # Reemplaza VALOR con el contenido real de tu .env

    echo -n "FALSE" | gcloud secrets versions add adk-google-genai-use-vertexai --data-file=-
    echo -n "TU_GOOGLE_API_KEY" | gcloud secrets versions add adk-google-api-key --data-file=-
    echo -n "TU_SERPAPI_KEY" | gcloud secrets versions add adk-serpapi-key --data-file=-
    echo -n "TU_NEWSAPI_KEY" | gcloud secrets versions add adk-newsapi-key --data-file=-
    echo -n "TU_CUSTOMER_ID" | gcloud secrets versions add adk-google-ads-customer-id --data-file=-
    echo -n "TU_LOGIN_CUSTOMER_ID" | gcloud secrets versions add adk-google-ads-login-customer-id --data-file=-
    echo -n "TU_DEVELOPER_TOKEN" | gcloud secrets versions add adk-google-ads-developer-token --data-file=-
    echo -n "TU_CLIENT_ID" | gcloud secrets versions add adk-google-ads-client-id --data-file=-
    echo -n "TU_CLIENT_SECRET" | gcloud secrets versions add adk-google-ads-client-secret --data-file=-
    echo -n "TU_REFRESH_TOKEN" | gcloud secrets versions add adk-google-ads-refresh-token --data-file=-
  EOT
}
