output "url" {
  value = "https://${var.domain}"
}

output "lb_ip" {
  value = google_compute_global_address.lb.address
}

output "registry" {
  description = "Préfixe des images (make p3-image)"
  value       = local.registry
}

output "image" {
  value = local.image
}

output "regions" {
  value = var.regions
}

output "api_service" {
  value = "${var.name_prefix}-api"
}

output "tickets_bucket" {
  value = google_storage_bucket.tickets.name
}

output "admin_token_secret" {
  description = "gcloud secrets versions access latest --secret <nom>"
  value       = google_secret_manager_secret.token["admin"].secret_id
}

output "staff_token_secret" {
  value = google_secret_manager_secret.token["staff"].secret_id
}
