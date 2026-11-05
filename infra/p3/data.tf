# --- Firestore : base transactionnelle multi-région ----------------------------------------------------
resource "google_firestore_database" "main" {
  name                              = "(default)"
  location_id                       = var.firestore_location
  type                              = "FIRESTORE_NATIVE"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"
  delete_protection_state           = "DELETE_PROTECTION_ENABLED"
  deletion_policy                   = "ABANDON"
  depends_on                        = [google_project_service.apis]
}

resource "google_firestore_backup_schedule" "daily" {
  database  = google_firestore_database.main.name
  retention = "604800s" # 7 jours
  daily_recurrence {}
}

# Index composites des requêtes de l'app (rattrapage et statistiques).
resource "google_firestore_index" "pending" {
  database   = google_firestore_database.main.name
  collection = "tickets"
  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
  fields {
    field_path = "created_at"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "by_event_status" {
  database   = google_firestore_database.main.name
  collection = "tickets"
  fields {
    field_path = "event_id"
    order      = "ASCENDING"
  }
  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
}

# --- Cloud Storage : QR codes (dual-région, réplication turbo) et front statique ------------------------
resource "google_storage_bucket" "tickets" {
  name                        = "${var.project_id}-tickets"
  location                    = "EU"
  rpo                         = "ASYNC_TURBO"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  custom_placement_config {
    data_locations = var.storage_regions
  }
  versioning {
    enabled = true
  }
  soft_delete_policy {
    retention_duration_seconds = 604800
  }
  lifecycle_rule {
    condition {
      num_newer_versions = 3
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "front" {
  name                        = "${var.project_id}-front"
  location                    = "EU"
  uniform_bucket_level_access = true
  force_destroy               = true
  website {
    main_page_suffix = "index.html"
  }
}

resource "google_storage_bucket_iam_member" "front_public" {
  bucket = google_storage_bucket.front.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_storage_bucket_object" "front_index" {
  bucket         = google_storage_bucket.front.name
  name           = "index.html"
  source         = "${path.module}/../../app/front/index.html"
  content_type   = "text/html; charset=utf-8"
  cache_control  = "public, max-age=60"
  detect_md5hash = filemd5("${path.module}/../../app/front/index.html")
}

# --- Événements « billet émis » vers BigQuery (remplace la nuit batch) ----------------------------------
resource "google_pubsub_topic" "ticket_issued" {
  name                       = "ticket-issued"
  message_retention_duration = "604800s"
  depends_on                 = [google_project_service.apis]
}

resource "google_bigquery_dataset" "sales" {
  dataset_id                 = "genarchi_sales"
  location                   = "EU"
  delete_contents_on_destroy = true
  depends_on                 = [google_project_service.apis]
}

resource "google_bigquery_table" "tickets_issued" {
  dataset_id          = google_bigquery_dataset.sales.dataset_id
  table_id            = "tickets_issued"
  deletion_protection = false
  time_partitioning {
    type = "DAY"
  }
  schema = jsonencode([
    { name = "ticket_id", type = "STRING", mode = "REQUIRED" },
    { name = "order_id", type = "STRING", mode = "NULLABLE" },
    { name = "event_id", type = "STRING", mode = "NULLABLE" },
    { name = "qr_object", type = "STRING", mode = "NULLABLE" },
    { name = "issued_at", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "ce_id", type = "STRING", mode = "NULLABLE" },
    { name = "ce_time", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_pubsub_subscription" "to_bigquery" {
  name  = "ticket-issued-to-bigquery"
  topic = google_pubsub_topic.ticket_issued.id
  bigquery_config {
    table               = "${google_bigquery_table.tickets_issued.project}.${google_bigquery_table.tickets_issued.dataset_id}.${google_bigquery_table.tickets_issued.table_id}"
    use_table_schema    = true
    drop_unknown_fields = true
  }
  depends_on = [google_bigquery_dataset_iam_member.pubsub_writes_sales]
}

# --- Secrets de l'application -------------------------------------------------------------------------
resource "random_password" "token" {
  for_each = toset(["admin", "staff"])
  length   = 40
  special  = false
}

resource "google_secret_manager_secret" "token" {
  for_each  = random_password.token
  secret_id = "${var.name_prefix}-${each.key}-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "token" {
  for_each    = random_password.token
  secret      = google_secret_manager_secret.token[each.key].id
  secret_data = each.value.result
}

resource "google_secret_manager_secret_iam_member" "api_reads_tokens" {
  for_each  = google_secret_manager_secret.token
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.sa.api}"
}

resource "google_secret_manager_secret_iam_member" "worker_reads_tokens" {
  for_each  = google_secret_manager_secret.token
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.sa.worker}"
}
