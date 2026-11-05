# --- Cloud Run : API et worker, une copie active par région --------------------------------------------
locals {
  secret_env = {
    ADMIN_TOKEN = google_secret_manager_secret.token["admin"].secret_id
    STAFF_TOKEN = google_secret_manager_secret.token["staff"].secret_id
  }
}

resource "google_cloud_run_v2_service" "api" {
  for_each             = toset(var.regions)
  name                 = "${var.name_prefix}-api"
  location             = each.value
  ingress              = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" # joignable seulement via le LB (et donc Cloud Armor)
  invoker_iam_disabled = true                                     # API publique : l'authentification est applicative
  default_uri_disabled = true
  deletion_protection  = false

  scaling {
    min_instance_count = var.min_instances
  }

  template {
    service_account                  = local.sa.api
    max_instance_request_concurrency = 80
    timeout                          = "30s"
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    containers {
      image = local.image
      args  = ["serve-api"]
      resources {
        limits            = { cpu = "1", memory = "512Mi" }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      dynamic "env" {
        for_each = merge(local.common_env, {
          EVENTS_BACKEND      = "none" # P3 : c'est Firestore qui émet l'événement
          REGION              = each.value
          CHAOS_FORCE_UNREADY = tostring(contains(var.chaos_unready_regions, each.value))
        })
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
      startup_probe {
        http_get { path = "/healthz" }
        period_seconds    = 2
        failure_threshold = 10
      }
      # Probe de readiness : c'est elle qui alimente « service health » et fait basculer le LB.
      readiness_probe {
        http_get { path = "/readyz" }
        period_seconds    = 5
        failure_threshold = 2
        timeout_seconds   = 2
      }
      liveness_probe {
        http_get { path = "/healthz" }
        period_seconds    = 10
        failure_threshold = 3
      }
    }
  }

  # La canary (scripts/canary.sh) déploie et répartit le trafic avec gcloud : ces champs lui appartiennent.
  lifecycle {
    ignore_changes = [client, client_version, traffic]
  }

  depends_on = [google_secret_manager_secret_iam_member.api_reads_tokens, google_project_iam_member.roles]
}

resource "google_cloud_run_v2_service" "worker" {
  for_each             = toset(var.regions)
  name                 = "${var.name_prefix}-worker"
  location             = each.value
  ingress              = "INGRESS_TRAFFIC_INTERNAL_ONLY" # seul Eventarc l'appelle
  default_uri_disabled = false
  deletion_protection  = false

  template {
    service_account                  = local.sa.worker
    max_instance_request_concurrency = 20
    timeout                          = "60s"
    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }
    containers {
      image = local.image
      args  = ["serve-worker"]
      resources {
        limits   = { cpu = "1", memory = "512Mi" }
        cpu_idle = true
      }
      dynamic "env" {
        for_each = merge(local.common_env, {
          EVENTS_BACKEND             = "pubsub"
          PUBSUB_PROJECT             = var.project_id
          PUBSUB_TOPIC_TICKET_ISSUED = google_pubsub_topic.ticket_issued.name
          REGION                     = each.value
        })
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.worker_reads_tokens, google_project_iam_member.roles]
}

# --- Eventarc : « document billet créé » dans Firestore → worker ---------------------------------------
# Un trigger par région : chaque événement est livré aux deux workers, l'émission étant idempotente (I5)
# le doublon ne coûte qu'une lecture. Une région perdue n'arrête pas l'émission.
resource "google_eventarc_trigger" "ticket_created" {
  for_each                = toset(var.regions)
  name                    = "${var.name_prefix}-ticket-created-${each.value}"
  location                = var.firestore_location
  service_account         = local.sa.events
  event_data_content_type = "application/json"

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.firestore.document.v1.created"
  }
  matching_criteria {
    attribute = "database"
    value     = google_firestore_database.main.name
  }
  matching_criteria {
    attribute = "document"
    operator  = "match-path-pattern"
    value     = "tickets/{ticket}"
  }

  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.worker[each.value].name
      region  = each.value
      path    = "/internal/events/ticket-created"
    }
  }

  depends_on = [google_cloud_run_v2_service_iam_member.events_invoke_worker, google_project_iam_member.roles]
}

# --- Rattrapage : Cloud Run job planifié toutes les 5 min, dans chaque région ---------------------------
resource "google_cloud_run_v2_job" "issue_pending" {
  for_each            = toset(var.regions)
  name                = "${var.name_prefix}-issue-pending"
  location            = each.value
  deletion_protection = false

  template {
    task_count = 1
    template {
      service_account = local.sa.worker
      timeout         = "240s"
      max_retries     = 1
      containers {
        image = local.image
        args  = ["issue-pending", "--older-than", "120", "--limit", "500"]
        resources {
          limits = { cpu = "1", memory = "512Mi" }
        }
        dynamic "env" {
          for_each = merge(local.common_env, {
            EVENTS_BACKEND             = "pubsub"
            PUBSUB_PROJECT             = var.project_id
            PUBSUB_TOPIC_TICKET_ISSUED = google_pubsub_topic.ticket_issued.name
            REGION                     = each.value
          })
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = local.secret_env
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.worker_reads_tokens]
}

resource "google_cloud_scheduler_job" "issue_pending" {
  for_each  = google_cloud_run_v2_job.issue_pending
  name      = "${var.name_prefix}-issue-pending-${each.key}"
  region    = each.key
  schedule  = "*/5 * * * *"
  time_zone = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${each.key}/jobs/${each.value.name}:run"
    oauth_token {
      service_account_email = local.sa.scheduler
    }
  }

  depends_on = [google_cloud_run_v2_job_iam_member.scheduler_runs_jobs]
}

# --- Test de panne de région (T4), nocturne -------------------------------------------------------------
# Le job rend l'API de la première région « non prête » pendant 10 min puis la rétablit.
# Le LB doit basculer seul : c'est ce que vérifient l'uptime check et le SLO pendant la fenêtre.
resource "google_cloud_run_v2_job" "chaos" {
  count               = var.chaos_enabled ? 1 : 0
  name                = "${var.name_prefix}-chaos-region"
  location            = local.primary
  deletion_protection = false

  template {
    task_count = 1
    template {
      service_account = local.sa.chaos
      timeout         = "1200s"
      max_retries     = 0
      containers {
        image   = "gcr.io/google.com/cloudsdktool/google-cloud-cli:stable"
        command = ["bash", "-c"]
        args = [<<-EOT
          set -euo pipefail
          svc="${var.name_prefix}-api"; region="${local.primary}"
          restore() { gcloud run services update "$svc" --region "$region" --update-env-vars CHAOS_FORCE_UNREADY=false --quiet; }
          trap restore EXIT
          echo "chaos: $svc@$region devient non prêt pendant $${CHAOS_SECONDS}s"
          gcloud run services update "$svc" --region "$region" --update-env-vars CHAOS_FORCE_UNREADY=true --quiet
          sleep "$CHAOS_SECONDS"
        EOT
        ]
        env {
          name  = "CHAOS_SECONDS"
          value = "600"
        }
      }
    }
  }
}

resource "google_cloud_scheduler_job" "chaos" {
  count     = var.chaos_enabled ? 1 : 0
  name      = "${var.name_prefix}-chaos-region"
  region    = local.primary
  schedule  = var.chaos_schedule
  time_zone = "Europe/Paris"

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${local.primary}/jobs/${google_cloud_run_v2_job.chaos[0].name}:run"
    oauth_token {
      service_account_email = local.sa.scheduler
    }
  }

  depends_on = [google_cloud_run_v2_job_iam_member.scheduler_runs_jobs]
}
