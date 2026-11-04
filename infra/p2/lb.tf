# --- Entrée publique : LB applicatif externe régional (TLS) → reverse proxies Apache des deux DC ---------
resource "google_compute_address" "lb" {
  name         = "p2-lb"
  region       = var.region
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
}

# Certificat géré par Google, prouvé par un CNAME dans Cloudflare (pas besoin que le LB réponde déjà).
resource "google_certificate_manager_dns_authorization" "main" {
  name       = "p2-dns-auth"
  location   = var.region
  domain     = var.domain
  type       = "PER_PROJECT_RECORD"
  depends_on = [google_project_service.apis]
}

resource "cloudflare_dns_record" "acme" {
  zone_id = var.cloudflare_zone_id
  name    = trimsuffix(google_certificate_manager_dns_authorization.main.dns_resource_record[0].name, ".")
  type    = google_certificate_manager_dns_authorization.main.dns_resource_record[0].type
  content = trimsuffix(google_certificate_manager_dns_authorization.main.dns_resource_record[0].data, ".")
  ttl     = 300
  proxied = false
  comment = "GenArchi P2 : autorisation DNS du certificat Google"
}

resource "google_certificate_manager_certificate" "main" {
  name     = "p2-cert"
  location = var.region
  managed {
    domains            = [var.domain]
    dns_authorizations = [google_certificate_manager_dns_authorization.main.id]
  }
}

resource "google_compute_region_health_check" "rp" {
  name                = "p2-rp"
  region              = var.region
  check_interval_sec  = 5
  timeout_sec         = 3
  healthy_threshold   = 2
  unhealthy_threshold = 2
  http_health_check {
    port         = 80
    request_path = "/rp-health"
  }
  log_config {
    enable = true
  }
}

resource "google_compute_region_backend_service" "rp" {
  name                  = "p2-rp"
  region                = var.region
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 30
  health_checks         = [google_compute_region_health_check.rp.id]

  dynamic "backend" {
    for_each = { for k, g in google_compute_instance_group.tier : k => g if startswith(k, "rp-") }
    content {
      group           = backend.value.id
      balancing_mode  = "UTILIZATION"
      capacity_scaler = 1
    }
  }

  log_config {
    enable      = true
    sample_rate = 1
  }
}

resource "google_compute_region_url_map" "https" {
  name            = "p2-https"
  region          = var.region
  default_service = google_compute_region_backend_service.rp.id
}

resource "google_compute_region_target_https_proxy" "main" {
  name                             = "p2-https"
  region                           = var.region
  url_map                          = google_compute_region_url_map.https.id
  certificate_manager_certificates = [google_certificate_manager_certificate.main.id]
}

resource "google_compute_forwarding_rule" "https" {
  name                  = "p2-https"
  region                = var.region
  load_balancing_scheme = "EXTERNAL_MANAGED"
  network_tier          = "PREMIUM"
  ip_address            = google_compute_address.lb.id
  port_range            = "443"
  network               = google_compute_network.main.id
  target                = google_compute_region_target_https_proxy.main.id
  depends_on            = [google_compute_subnetwork.proxy_only]
}

resource "google_compute_region_url_map" "redirect" {
  name   = "p2-redirect"
  region = var.region
  default_url_redirect {
    https_redirect         = true
    strip_query            = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

resource "google_compute_region_target_http_proxy" "redirect" {
  name    = "p2-redirect"
  region  = var.region
  url_map = google_compute_region_url_map.redirect.id
}

resource "google_compute_forwarding_rule" "http" {
  name                  = "p2-http"
  region                = var.region
  load_balancing_scheme = "EXTERNAL_MANAGED"
  network_tier          = "PREMIUM"
  ip_address            = google_compute_address.lb.id
  port_range            = "80"
  network               = google_compute_network.main.id
  target                = google_compute_region_target_http_proxy.redirect.id
  depends_on            = [google_compute_subnetwork.proxy_only]
}

resource "cloudflare_dns_record" "app" {
  zone_id = var.cloudflare_zone_id
  name    = var.domain
  type    = "A"
  content = google_compute_address.lb.address
  ttl     = 300
  proxied = false
  comment = "GenArchi P2, géré par OpenTofu (dépôt 3-Istor/GenArchi)"
}

# --- IP virtuelles internes : LB passthrough, le health check désigne le serveur actif ---------------------
locals {
  internal_vips = {
    # PostgreSQL : seul le primaire Patroni répond 200 sur /primary.
    db = { ip = local.db_vip, port = "5432", hc_port = 8008, hc_path = "/primary" }
    # NFS : seul le NAS qui porte le disque fait tourner nfs-server.
    nas = { ip = local.nas_vip, port = "2049", hc_port = 2049, hc_path = "" }
  }
}

resource "google_compute_region_health_check" "vip" {
  for_each            = local.internal_vips
  name                = "p2-${each.key}-active"
  region              = var.region
  check_interval_sec  = 3
  timeout_sec         = 2
  healthy_threshold   = 2
  unhealthy_threshold = 2

  dynamic "http_health_check" {
    for_each = each.value.hc_path != "" ? [1] : []
    content {
      port         = each.value.hc_port
      request_path = each.value.hc_path
    }
  }
  dynamic "tcp_health_check" {
    for_each = each.value.hc_path == "" ? [1] : []
    content {
      port = each.value.hc_port
    }
  }
  log_config {
    enable = true
  }
}

resource "google_compute_region_backend_service" "vip" {
  for_each              = local.internal_vips
  name                  = "p2-${each.key}"
  region                = var.region
  load_balancing_scheme = "INTERNAL"
  protocol              = "TCP"
  health_checks         = [google_compute_region_health_check.vip[each.key].id]
  # Une connexion ouverte reste sur son serveur ; à la bascule, l'app se reconnecte (pool psycopg, montage NFS hard).
  connection_draining_timeout_sec = 0

  dynamic "backend" {
    for_each = { for k, g in google_compute_instance_group.tier : k => g if startswith(k, "${each.key}-") }
    content {
      group          = backend.value.id
      balancing_mode = "CONNECTION"
    }
  }
}

resource "google_compute_forwarding_rule" "vip" {
  for_each              = local.internal_vips
  name                  = "p2-${each.key}-vip"
  region                = var.region
  load_balancing_scheme = "INTERNAL"
  ip_protocol           = "TCP"
  ip_address            = each.value.ip
  ports                 = [each.value.port]
  network               = google_compute_network.main.id
  subnetwork            = google_compute_subnetwork.tier["data"].id
  backend_service       = google_compute_region_backend_service.vip[each.key].id
}
