# --- Observabilité : sonde externe, SLO de disponibilité et alerte de burn rate --------------------------
resource "google_monitoring_notification_channel" "email" {
  count        = var.alert_email != "" ? 1 : 0
  display_name = "GenArchi P3 — équipe"
  type         = "email"
  labels       = { email_address = var.alert_email }
}

resource "google_monitoring_uptime_check_config" "readyz" {
  display_name = "${var.name_prefix} readyz"
  timeout      = "10s"
  period       = "60s"
  http_check {
    path         = "/readyz"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }
  monitored_resource {
    type   = "uptime_url"
    labels = { project_id = var.project_id, host = var.domain }
  }
}

resource "google_monitoring_custom_service" "api" {
  service_id   = "${var.name_prefix}-api"
  display_name = "GenArchi P3 API"
}

# 99,9 % des requêtes du LB sans 5xx sur 28 jours glissants (contrat P3, § 2).
resource "google_monitoring_slo" "availability" {
  service             = google_monitoring_custom_service.api.service_id
  slo_id              = "availability"
  display_name        = "99,9 % des requêtes sans erreur 5xx"
  goal                = 0.999
  rolling_period_days = 28
  request_based_sli {
    good_total_ratio {
      total_service_filter = join(" AND ", [
        "metric.type=\"loadbalancing.googleapis.com/https/request_count\"",
        "resource.type=\"https_lb_rule\"",
        "resource.label.\"backend_target_name\"=\"${google_compute_backend_service.api.name}\"",
      ])
      bad_service_filter = join(" AND ", [
        "metric.type=\"loadbalancing.googleapis.com/https/request_count\"",
        "resource.type=\"https_lb_rule\"",
        "resource.label.\"backend_target_name\"=\"${google_compute_backend_service.api.name}\"",
        "metric.label.\"response_code_class\"=\"500\"",
      ])
    }
  }
}

# Alerte « budget d'erreur consommé 10× trop vite sur 1 h » (règle multi-fenêtres simplifiée).
resource "google_monitoring_alert_policy" "burn_rate" {
  display_name          = "${var.name_prefix} SLO burn rate"
  combiner              = "OR"
  notification_channels = google_monitoring_notification_channel.email[*].id
  conditions {
    display_name = "burn rate > 10 sur 1 h"
    condition_threshold {
      filter          = "select_slo_burn_rate(\"${google_monitoring_slo.availability.name}\", \"3600s\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      duration        = "0s"
    }
  }
  documentation {
    content   = "Runbook : docs/runbooks/p3-incident.md"
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "uptime" {
  display_name          = "${var.name_prefix} sonde readyz en échec"
  combiner              = "OR"
  notification_channels = google_monitoring_notification_channel.email[*].id
  conditions {
    display_name = "readyz KO depuis 2 sondes régionales"
    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\" AND metric.label.check_id=\"${google_monitoring_uptime_check_config.readyz.uptime_check_id}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "120s"
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.project_id"]
      }
    }
  }
}
