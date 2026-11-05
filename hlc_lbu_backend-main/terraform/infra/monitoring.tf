# ══════════════════════════════════════════════════════════════════════════════
# monitoring.tf – Uptime Check + Alertas de Cloud Monitoring
#
# Solo se crea si alert_email != "" en el tfvars del ambiente.
# ══════════════════════════════════════════════════════════════════════════════

locals {
  monitoring_enabled = var.alert_email != ""
}

# ── Canal de notificación por email ───────────────────────────────────────────

resource "google_monitoring_notification_channel" "email" {
  count        = local.monitoring_enabled ? 1 : 0
  display_name = "[${upper(local.env)}] HiLuca LBU – Email Alert"
  type         = "email"
  project      = local.project

  labels = {
    email_address = var.alert_email
  }
}

# ── Uptime Check HTTPS ────────────────────────────────────────────────────────

resource "google_monitoring_uptime_check_config" "https" {
  count        = local.monitoring_enabled ? 1 : 0
  display_name = "[${upper(local.env)}] ${var.domain} – HTTPS Uptime"
  project      = local.project
  timeout      = "10s"
  period       = "60s"   # Revisa cada minuto

  http_check {
    path         = var.health_check_path
    port         = 443
    use_ssl      = true
    validate_ssl = true
    request_method = "GET"
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = local.project
      host       = var.domain
    }
  }

  content_matchers {
    content = "OK"
    matcher = "CONTAINS_STRING"
  }
}

# ── Política de alerta: servicio caído ────────────────────────────────────────

resource "google_monitoring_alert_policy" "uptime_failed" {
  count        = local.monitoring_enabled ? 1 : 0
  display_name = "[${upper(local.env)}] ${var.domain} – Servicio caído"
  project      = local.project
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Uptime check falló"

    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
        "resource.type=\"uptime_url\"",
        "metric.label.\"check_id\"=\"${google_monitoring_uptime_check_config.https[0].uptime_check_id}\"",
      ])

      comparison      = "COMPARISON_LT"
      threshold_value = 1
      duration        = "60s"   # Alerta si falla por > 1 min

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.*"]
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email[0].id,
  ]

  alert_strategy {
    auto_close = "1800s"  # Cierra la alerta automáticamente si se recupera en 30 min
  }

  documentation {
    content   = "El servicio **${var.domain}** [${upper(local.env)}] no está respondiendo. Revisa la VM `${local.prefix}-vm` y el stack de Docker Compose."
    mime_type = "text/markdown"
  }
}

# ── Política de alerta: alta latencia ────────────────────────────────────────

resource "google_monitoring_alert_policy" "high_latency" {
  count        = local.monitoring_enabled ? 1 : 0
  display_name = "[${upper(local.env)}] ${var.domain} – Alta latencia LB"
  project      = local.project
  combiner     = "OR"
  enabled      = local.env == "prd"  # Solo activa en producción

  conditions {
    display_name = "Latencia P99 > 5s en el Load Balancer"

    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"loadbalancing.googleapis.com/https/backend_latencies\"",
        "resource.type=\"https_lb_rule\"",
        "resource.label.\"backend_target_name\"=\"${local.prefix}-backend\"",
      ])

      comparison      = "COMPARISON_GT"
      threshold_value = 5000  # 5000ms = 5s
      duration        = "120s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_99"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.label.backend_target_name"]
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email[0].id,
  ]

  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content   = "El backend **${local.prefix}** está respondiendo con P99 > 5s. Revisa la carga de la VM y el estado de Cloud SQL."
    mime_type = "text/markdown"
  }
}
