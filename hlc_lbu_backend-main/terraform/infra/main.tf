# ══════════════════════════════════════════════════════════════════════════════
# main.tf – HiLuca LBU Infrastructure (Multi-Environment)
# Compute Engine + Cloud SQL (PostgreSQL 14) + HTTP(S) Load Balancer
#
# Uso por ambiente:
#   terraform workspace new dev && terraform apply -var-file=env/dev.tfvars
#   terraform workspace new qas && terraform apply -var-file=env/qas.tfvars
#   terraform workspace new prd && terraform apply -var-file=env/prd.tfvars
# ══════════════════════════════════════════════════════════════════════════════

# El bloque terraform {} (backend + required_providers) vive en backend.tf


locals {
  project     = var.project_id
  region      = var.region
  zone        = var.zone
  env         = var.environment
  prefix      = "hiluca-lbu-${var.environment}" # ej: hiluca-lbu-dev
  ar_prefix   = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"

  labels = {
    app         = "hiluca-lbu"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# APIs
# ══════════════════════════════════════════════════════════════════════════════

resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
  ])
  project            = local.project
  service            = each.value
  disable_on_destroy = false
}

# ══════════════════════════════════════════════════════════════════════════════
# Service Account para la VM (uno por ambiente)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_service_account" "vm_sa" {
  account_id   = "${local.prefix}-vm-sa"
  display_name = "HiLuca LBU [${upper(local.env)}] – Compute Engine SA"
  project      = local.project
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "vm_sql_client" {
  project = local.project
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.vm_sa.email}"
}

resource "google_project_iam_member" "vm_secret_accessor" {
  project = local.project
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.vm_sa.email}"
}

resource "google_project_iam_member" "vm_artifact_reader" {
  project = local.project
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.vm_sa.email}"
}

resource "google_project_iam_member" "vm_log_writer" {
  project = local.project
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.vm_sa.email}"
}

resource "google_project_iam_member" "vm_metric_writer" {
  project = local.project
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.vm_sa.email}"
}

# ══════════════════════════════════════════════════════════════════════════════
# Secret Manager – .env por ambiente
# ══════════════════════════════════════════════════════════════════════════════

resource "google_secret_manager_secret" "env_file" {
  secret_id = var.env_secret_name   # ej: hiluca-lbu-dev-env
  project   = local.project
  labels    = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# Para cargar el contenido del .env:
#   gcloud secrets versions add hiluca-lbu-dev-env --data-file=".env.dev"
#   gcloud secrets versions add hiluca-lbu-qas-env --data-file=".env.qas"
#   gcloud secrets versions add hiluca-lbu-prd-env --data-file=".env.prd"

# ══════════════════════════════════════════════════════════════════════════════
# Cloud SQL – PostgreSQL 14 (instancia por ambiente)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_compute_network" "vpc_network" {
  name = "private-network"
}

resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
  project       = local.project
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

resource "google_sql_database_instance" "postgres" {
  name             = "${local.prefix}-postgres"
  database_version = "POSTGRES_14"
  region           = local.region
  project          = local.project

  depends_on = [google_service_networking_connection.private_vpc_connection,google_project_service.apis]

  deletion_protection = var.db_deletion_protection

  settings {
    tier            = var.db_tier
    disk_autoresize = true
    disk_size       = var.db_disk_size_gb

    user_labels = local.labels

    ip_configuration {
      ipv4_enabled = false # Desactiva la IP pública
      private_network = google_compute_network.vpc_network.id
      # Auth Proxy maneja la autenticación – no se necesitan authorized_networks adicionales.
    }

    backup_configuration {
      enabled                        = var.db_enable_backups
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.db_enable_backups
      transaction_log_retention_days = var.db_enable_backups ? 7 : null
      dynamic "backup_retention_settings" {
        for_each = var.db_enable_backups ? [1] : []
        content {
          retained_backups = 7
          retention_unit   = "COUNT"
        }
      }
    }

    maintenance_window {
      day          = 7  # Domingo
      hour         = 4
      update_track = "stable"
    }

    database_flags {
      name  = "max_connections"
      value = var.environment == "prd" ? "200" : "50"
    }

    insights_config {
      query_insights_enabled  = var.environment != "dev"
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false
    }
  }
}

resource "google_sql_database" "strapi" {
  name     = var.db_name_strapi
  instance = google_sql_database_instance.postgres.name
  project  = local.project
}

resource "google_sql_database" "sinergia" {
  name     = var.db_name_sinergia
  instance = google_sql_database_instance.postgres.name
  project  = local.project
}

resource "google_sql_database" "fury_langfuse" {
  name     = var.db_name_fury
  instance = google_sql_database_instance.postgres.name
  project  = local.project
}

resource "google_sql_user" "postgres_user" {
  name     = var.db_user_postgres
  instance = google_sql_database_instance.postgres.name
  password = var.db_password_postgres
  project  = local.project
}

resource "google_sql_user" "app_user" {
  name     = var.db_user
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
  project  = local.project
}

# ══════════════════════════════════════════════════════════════════════════════
# Firewall Rules (por ambiente, con tags de red por ambiente)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_compute_firewall" "allow_ssh" {
  name    = "${local.prefix}-allow-ssh"
  network = "default"
  project = local.project

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = [local.prefix]

  description = "[${upper(local.env)}] SSH para GitHub Actions"
}

resource "google_compute_firewall" "allow_lb_health_check" {
  name    = "${local.prefix}-allow-lb-hc"
  network = "default"
  project = local.project

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = [
    "130.211.0.0/22",  # GCP LB health check
    "35.191.0.0/16",
  ]
  target_tags = [local.prefix]

  description = "[${upper(local.env)}] GCP LB health checks → VM:80"
}

# ══════════════════════════════════════════════════════════════════════════════
# VM Image (Ubuntu 22.04 LTS)
# ══════════════════════════════════════════════════════════════════════════════

data "google_compute_image" "debian_12" {
  family  = "debian-12"
  project = "debian-cloud"
}

# ══════════════════════════════════════════════════════════════════════════════
# Compute Engine Instance (una por ambiente)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_compute_instance" "vm" {
  name         = "${local.prefix}-vm"
  machine_type = var.vm_machine_type
  zone         = local.zone
  project      = local.project

  tags   = [local.prefix]  # tag de red con el ambiente
  labels = local.labels

  boot_disk {
    initialize_params {
      image = data.google_compute_image.debian_12.self_link
      size  = var.vm_disk_size_gb
      type  = "pd-ssd"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  service_account {
    email  = google_service_account.vm_sa.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    google-logging-enabled    = "true"
    google-monitoring-enabled = "true"
    ssh-keys                  = "debian:${var.gh_actions_ssh_public_key}"

    startup-script = templatefile("${path.module}/scripts/startup.sh", {
      project_id          = local.project
      environment         = local.env
      env_secret_name     = var.env_secret_name
      sql_connection_name = google_sql_database_instance.postgres.connection_name
      ar_prefix           = local.ar_prefix
      region              = local.region
      db_admin_user       = var.db_user
      db_name_strapi      = var.db_name_strapi
      db_name_sinergia    = var.db_name_sinergia
      db_reader_password  = var.db_reader_password
      db_writer_password  = var.db_writer_password
    })

    # Script de provisioning de usuarios – leído desde metadata en startup.sh
    init-db-users-script = templatefile("${path.module}/scripts/init_db_users.sh", {
      db_admin_user      = var.db_user
      db_name_strapi     = var.db_name_strapi
      db_name_sinergia   = var.db_name_sinergia
      db_reader_password = var.db_reader_password
      db_writer_password = var.db_writer_password
      sql_connection_name = google_sql_database_instance.postgres.connection_name
    })
  }

  allow_stopping_for_update = true

  depends_on = [
    google_project_iam_member.vm_sql_client,
    google_project_iam_member.vm_secret_accessor,
    google_project_iam_member.vm_artifact_reader,
    google_sql_database_instance.postgres,
    google_secret_manager_secret.env_file,
  ]
}

# ══════════════════════════════════════════════════════════════════════════════
# Instance Group (no administrado – una VM por ambiente)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_compute_instance_group" "group" {
  name    = "${local.prefix}-group"
  zone    = local.zone
  project = local.project

  instances = [google_compute_instance.vm.self_link]

  named_port {
    name = "http"
    port = 80
  }
}

# ══════════════════════════════════════════════════════════════════════════════
# Load Balancer – HTTP(S) Global External (uno por ambiente)
# ══════════════════════════════════════════════════════════════════════════════

resource "google_compute_global_address" "lb_ip" {
  name    = "${local.prefix}-lb-ip"
  project = local.project
}

resource "google_compute_health_check" "http" {
  name    = "${local.prefix}-http-health-check"
  project = local.project

  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3

  http_health_check {
    port         = 80
    request_path = var.health_check_path
  }
}

resource "google_compute_backend_service" "default" {
  name                  = "${local.prefix}-backend"
  project               = local.project
  protocol              = "HTTP"
  port_name             = "http"
  load_balancing_scheme = "EXTERNAL"
  timeout_sec           = 60

  # Cloud Armor WAF (solo si enable_cloud_armor = true)
  security_policy = var.enable_cloud_armor ? google_compute_security_policy.waf[0].id : null

  backend {
    group           = google_compute_instance_group.group.id
    balancing_mode  = "UTILIZATION"
    max_utilization = 0.8
    capacity_scaler = 1.0
  }

  health_checks = [google_compute_health_check.http.id]

  log_config {
    enable      = true
    sample_rate = local.env == "prd" ? 1.0 : 0.5
  }
}

resource "google_compute_url_map" "https" {
  name            = "${local.prefix}-https-urlmap"
  project         = local.project
  default_service = google_compute_backend_service.default.id
}

resource "google_compute_url_map" "http_redirect" {
  name    = "${local.prefix}-http-redirect"
  project = local.project

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

# ── Data sources: cert y key desde Secret Manager ────────────────────────────
data "google_secret_manager_secret_version" "ssl_cert" {
  secret  = var.ssl_cert_secret_name
  project = local.project
}

data "google_secret_manager_secret_version" "ssl_key" {
  secret  = var.ssl_key_secret_name
  project = local.project
}

# Certificado SSL self-managed (leído de Secret Manager)
resource "google_compute_ssl_certificate" "default" {
  name        = "${local.prefix}-ssl-cert"
  project     = local.project
  certificate = data.google_secret_manager_secret_version.ssl_cert.secret_data
  private_key = data.google_secret_manager_secret_version.ssl_key.secret_data

  # Crea el nuevo cert antes de destruir el anterior (zero-downtime rotation)
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_target_http_proxy" "http" {
  name    = "${local.prefix}-http-proxy"
  project = local.project
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_target_https_proxy" "https" {
  name             = "${local.prefix}-https-proxy"
  project          = local.project
  url_map          = google_compute_url_map.https.id
  ssl_certificates = [google_compute_ssl_certificate.default.id]
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "${local.prefix}-http-rule"
  project               = local.project
  ip_address            = google_compute_global_address.lb_ip.address
  port_range            = "80"
  target                = google_compute_target_http_proxy.http.id
  load_balancing_scheme = "EXTERNAL"
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "${local.prefix}-https-rule"
  project               = local.project
  ip_address            = google_compute_global_address.lb_ip.address
  port_range            = "443"
  target                = google_compute_target_https_proxy.https.id
  load_balancing_scheme = "EXTERNAL"
}
