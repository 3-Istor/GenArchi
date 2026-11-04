# Amorçage, lancé une seule fois avec un état local : bucket d'état OpenTofu partagé par l'équipe.
# Ensuite, infra/p2 et infra/p3 stockent leur état dans ce bucket (verrouillage natif GCS).
terraform {
  required_version = ">= 1.11"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 8.8" }
  }
}

variable "project_id" {
  description = "Projet qui héberge l'état (en pratique celui de la P3)"
  type        = string
}

variable "bucket_name" {
  type    = string
  default = "genarchi-tfstate"
}

variable "team_members" {
  description = "Comptes Google de l'équipe qui lancent tofu (user:prenom@...)"
  type        = list(string)
  default     = []
}

provider "google" {
  project = var.project_id
  region  = "europe-west1"
}

resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_storage_bucket" "state" {
  name                        = var.bucket_name
  location                    = "EU"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning {
    enabled = true
  }
  lifecycle_rule {
    condition {
      num_newer_versions = 20
    }
    action {
      type = "Delete"
    }
  }
  lifecycle {
    prevent_destroy = true
  }
  depends_on = [google_project_service.storage]
}

resource "google_storage_bucket_iam_member" "team" {
  for_each = toset(var.team_members)
  bucket   = google_storage_bucket.state.name
  role     = "roles/storage.objectUser"
  member   = each.value
}

output "bucket" {
  value = google_storage_bucket.state.name
}
