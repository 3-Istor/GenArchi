# Un compte de service par composant, droits minimaux (spec P3, § 4).
resource "google_service_account" "sa" {
  for_each     = toset(["api", "worker", "events", "scheduler", "chaos"])
  account_id   = "${var.name_prefix}-${each.key}"
  display_name = "GenArchi P3 ${each.key}"
}

locals {
  sa = { for k, v in google_service_account.sa : k => v.email }
  project_roles = {
    api    = ["roles/datastore.user", "roles/cloudtrace.agent"]
    worker = ["roles/datastore.user", "roles/cloudtrace.agent"]
    events = ["roles/eventarc.eventReceiver"]
  }
}

resource "google_project_iam_member" "roles" {
  for_each = { for pair in flatten([for sa, roles in local.project_roles : [for r in roles : { sa = sa, role = r }]]) : "${pair.sa}-${pair.role}" => pair }
  project  = var.project_id
  role     = each.value.role
  member   = "serviceAccount:${local.sa[each.value.sa]}"
}

# L'API signe les URL des QR avec sa propre identité (signBlob) : pas de clé exportée.
resource "google_service_account_iam_member" "api_signs_urls" {
  service_account_id = google_service_account.sa["api"].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${local.sa.api}"
}

resource "google_storage_bucket_iam_member" "api_reads_tickets" {
  bucket = google_storage_bucket.tickets.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${local.sa.api}"
}

resource "google_storage_bucket_iam_member" "worker_writes_tickets" {
  for_each = toset(["roles/storage.objectCreator", "roles/storage.objectViewer"])
  bucket   = google_storage_bucket.tickets.name
  role     = each.value
  member   = "serviceAccount:${local.sa.worker}"
}

resource "google_pubsub_topic_iam_member" "worker_publishes" {
  topic  = google_pubsub_topic.ticket_issued.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${local.sa.worker}"
}

# Eventarc et Cloud Scheduler invoquent les services et jobs Cloud Run.
resource "google_cloud_run_v2_service_iam_member" "events_invoke_worker" {
  for_each = google_cloud_run_v2_service.worker
  name     = each.value.name
  location = each.value.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.sa.events}"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_runs_jobs" {
  for_each = merge(
    { for r, j in google_cloud_run_v2_job.issue_pending : "issue-${r}" => j },
    var.chaos_enabled ? { chaos = google_cloud_run_v2_job.chaos[0] } : {},
  )
  name     = each.value.name
  location = each.value.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.sa.scheduler}"
}

# Le test de panne modifie l'API d'une région puis la rétablit : il agit via l'API Cloud Run.
resource "google_cloud_run_v2_service_iam_member" "chaos_manages_api" {
  for_each = var.chaos_enabled ? google_cloud_run_v2_service.api : {}
  name     = each.value.name
  location = each.value.location
  role     = "roles/run.developer"
  member   = "serviceAccount:${local.sa.chaos}"
}

resource "google_service_account_iam_member" "chaos_acts_as_api" {
  count              = var.chaos_enabled ? 1 : 0
  service_account_id = google_service_account.sa["api"].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.sa.chaos}"
}

# Pub/Sub écrit dans BigQuery avec son agent de service.
resource "google_bigquery_dataset_iam_member" "pubsub_writes_sales" {
  dataset_id = google_bigquery_dataset.sales.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
