# --- Entrée publique : LB HTTP(S) global, Cloud Armor, CDN pour le front --------------------------------
resource "google_compute_global_address" "lb" {
  name       = "${var.name_prefix}-lb"
  depends_on = [google_project_service.apis]
}

resource "google_compute_region_network_endpoint_group" "api" {
  for_each              = google_cloud_run_v2_service.api
  name                  = "${var.name_prefix}-api-${each.key}"
  region                = each.key
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = each.value.name
  }
}

resource "google_compute_security_policy" "edge" {
  name        = "${var.name_prefix}-edge"
  description = "WAF et limitation de débit devant l'API"
  type        = "CLOUD_ARMOR"

  rule {
    action      = "deny(403)"
    priority    = 1000
    description = "Injections SQL et XSS (règles OWASP préconfigurées)"
    match {
      expr {
        expression = "evaluatePreconfiguredWaf('sqli-v33-stable', {'sensitivity': 1}) || evaluatePreconfiguredWaf('xss-v33-stable', {'sensitivity': 1})"
      }
    }
  }

  rule {
    action      = "throttle"
    priority    = 2000
    description = "Au plus 600 requêtes par minute et par IP"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 600
        interval_sec = 60
      }
    }
  }

  rule {
    action      = "allow"
    priority    = 2147483647
    description = "Règle par défaut"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_backend_service" "api" {
  name                  = "${var.name_prefix}-api"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTPS"
  security_policy       = google_compute_security_policy.edge.id

  dynamic "backend" {
    for_each = google_compute_region_network_endpoint_group.api
    content {
      group = backend.value.id
    }
  }

  log_config {
    enable      = true
    sample_rate = 1
  }
}

resource "google_compute_backend_bucket" "front" {
  name        = "${var.name_prefix}-front"
  bucket_name = google_storage_bucket.front.name
  enable_cdn  = true
  cdn_policy {
    cache_mode  = "CACHE_ALL_STATIC"
    default_ttl = 60
    max_ttl     = 3600
  }
}

resource "google_compute_url_map" "https" {
  name            = "${var.name_prefix}-https"
  default_service = google_compute_backend_bucket.front.id

  host_rule {
    hosts        = ["*"]
    path_matcher = "app"
  }

  path_matcher {
    name            = "app"
    default_service = google_compute_backend_bucket.front.id
    path_rule {
      paths   = local.api_paths
      service = google_compute_backend_service.api.id
    }
  }
}

resource "google_compute_managed_ssl_certificate" "main" {
  name = "${var.name_prefix}-cert"
  managed {
    domains = [var.domain]
  }
}

resource "google_compute_target_https_proxy" "main" {
  name             = "${var.name_prefix}-https"
  url_map          = google_compute_url_map.https.id
  ssl_certificates = [google_compute_managed_ssl_certificate.main.id]
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "${var.name_prefix}-https"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb.address
  port_range            = "443"
  target                = google_compute_target_https_proxy.main.id
}

# HTTP → HTTPS
resource "google_compute_url_map" "redirect" {
  name = "${var.name_prefix}-redirect"
  default_url_redirect {
    https_redirect         = true
    strip_query            = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

resource "google_compute_target_http_proxy" "redirect" {
  name    = "${var.name_prefix}-redirect"
  url_map = google_compute_url_map.redirect.id
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "${var.name_prefix}-http"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb.address
  port_range            = "80"
  target                = google_compute_target_http_proxy.redirect.id
}

# Nom public dans la zone Cloudflare existante (non proxifié : le certificat Google doit voir le LB).
resource "cloudflare_dns_record" "app" {
  zone_id = var.cloudflare_zone_id
  name    = var.domain
  type    = "A"
  content = google_compute_global_address.lb.address
  ttl     = 300
  proxied = false
  comment = "GenArchi P3, géré par OpenTofu (dépôt 3-Istor/GenArchi)"
}
