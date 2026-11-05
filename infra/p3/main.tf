provider "google" {
  project               = var.project_id
  region                = var.regions[0]
  default_labels        = var.labels
  user_project_override = true
  billing_project       = var.project_id
}

# Jeton lu dans CLOUDFLARE_API_TOKEN (droit « DNS edit » sur la zone 3istor.com).
provider "cloudflare" {}

data "google_project" "this" {}

locals {
  primary   = var.regions[0]
  image     = var.app_image != "" ? var.app_image : "${local.registry}/genarchi:latest"
  registry  = "europe-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}"
  base_url  = "https://${var.domain}"
  api_paths = ["/events", "/events/*", "/orders/*", "/tickets/*", "/t/*", "/admin/*", "/internal/chaos", "/healthz", "/readyz", "/version", "/docs", "/openapi.json"]

  common_env = {
    PLATFORM          = "p3"
    LOG_LEVEL         = "INFO"
    PUBLIC_BASE_URL   = local.base_url
    DATA_BACKEND      = "firestore"
    FIRESTORE_PROJECT = var.project_id
    BLOB_BACKEND      = "gcs"
    BLOB_GCS_BUCKET   = google_storage_bucket.tickets.name
    CHAOS_ENABLED     = tostring(var.chaos_enabled)
    APP_VERSION       = var.app_version
  }
}

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com", "firestore.googleapis.com", "eventarc.googleapis.com", "pubsub.googleapis.com",
    "storage.googleapis.com", "compute.googleapis.com", "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com", "cloudbuild.googleapis.com", "cloudscheduler.googleapis.com",
    "monitoring.googleapis.com", "logging.googleapis.com", "bigquery.googleapis.com",
    "iamcredentials.googleapis.com", "cloudtrace.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "app" {
  repository_id = "genarchi"
  location      = "europe"
  format        = "DOCKER"
  description   = "Images de l'application GenArchi"
  cleanup_policies {
    id     = "garder-20-dernieres"
    action = "KEEP"
    most_recent_versions { keep_count = 20 }
  }
  depends_on = [google_project_service.apis]
}
