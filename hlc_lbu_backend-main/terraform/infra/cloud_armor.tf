# ══════════════════════════════════════════════════════════════════════════════
# cloud_armor.tf – WAF básico con Cloud Armor
#
# Solo se crea si enable_cloud_armor = true en el tfvars del ambiente.
# Recomendado: false en dev (ahorra costos), true en qas y prd.
#
# Costo Cloud Armor Standard: ~$5/mes por política + $1/millón de requests.
# ══════════════════════════════════════════════════════════════════════════════

resource "google_compute_security_policy" "waf" {
  count   = var.enable_cloud_armor ? 1 : 0
  name    = "${local.prefix}-waf"
  project = local.project

  description = "WAF [${upper(local.env)}] – HiLuca LBU"

  # ── Reglas WAF preconfiguradas (Cloud Armor Standard) ─────────────────────

  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-stable')"
      }
    }
    description = "Bloquear SQL Injection"
  }

  rule {
    action   = "deny(403)"
    priority = 1001
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-stable')"
      }
    }
    description = "Bloquear Cross-Site Scripting (XSS)"
  }

  rule {
    action   = "deny(403)"
    priority = 1002
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('lfi-stable')"
      }
    }
    description = "Bloquear Local File Inclusion (LFI)"
  }

  rule {
    action   = "deny(403)"
    priority = 1003
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('rfi-stable')"
      }
    }
    description = "Bloquear Remote File Inclusion (RFI)"
  }

  # ── Regla por defecto: permitir todo lo demás ──────────────────────────────
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default: permitir tráfico"
  }
}
