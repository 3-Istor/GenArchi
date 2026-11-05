resource "google_compute_network" "main" {
  name                    = "p2-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "tier" {
  for_each                 = local.subnets
  name                     = "p2-${each.key}"
  region                   = var.region
  network                  = google_compute_network.main.id
  ip_cidr_range            = each.value
  private_ip_google_access = true
  log_config {
    aggregation_interval = "INTERVAL_5_MIN"
    flow_sampling        = 0.5
  }
}

# Sous-réseau réservé aux proxys Envoy du load balancer régional.
resource "google_compute_subnetwork" "proxy_only" {
  name          = "p2-proxy-only"
  region        = var.region
  network       = google_compute_network.main.id
  ip_cidr_range = local.proxy_only_cidr
  purpose       = "REGIONAL_MANAGED_PROXY"
  role          = "ACTIVE"
}

# Sortie Internet (paquets Debian, PyPI) sans IP publique sur les VM.
resource "google_compute_router" "main" {
  name    = "p2-router"
  region  = var.region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "main" {
  name                               = "p2-nat"
  router                             = google_compute_router.main.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# --- Pare-feu : tout est fermé (règle implicite), chaque flux autorisé est listé, par plage d'adresses -----
locals {
  firewall = {
    iap-to-bastion = { src = [local.iap_range], tags = ["bastion"], ports = ["22"] }
    bastion-ssh    = { src = ["${local.host_ip.bastion}/32"], tags = ["p2"], ports = ["22"] }
    lb-to-rp       = { src = concat([local.proxy_only_cidr], local.gcp_health_check_ranges), tags = ["rp"], ports = ["80"] }
    rp-to-app      = { src = [local.subnets.dmz], tags = ["app"], ports = ["8080"] }
    app-to-db      = { src = [local.subnets.app], tags = ["db"], ports = ["5432"] }
    app-to-mq      = { src = [local.subnets.app], tags = ["mq", "witness"], ports = ["5672"] }
    app-to-nas     = { src = [local.subnets.app], tags = ["nas"], ports = ["2049"] }
    hc-to-db       = { src = local.gcp_health_check_ranges, tags = ["db"], ports = ["8008"] }
    hc-to-nas      = { src = local.gcp_health_check_ranges, tags = ["nas"], ports = ["2049"] }
    db-cluster     = { src = [local.subnets.data], tags = ["db", "witness"], ports = ["5432", "8008", "2379", "2380"] }
    mq-cluster     = { src = [local.subnets.data], tags = ["mq", "witness"], ports = ["4369", "25672", "35672-35682"] }
    backup-to-db   = { src = ["${local.host_ip.backup}/32"], tags = ["db"], ports = ["5432", "8008"] }
    zabbix-passive = { src = ["${local.host_ip.monitoring}/32"], tags = ["p2"], ports = ["10050"] }
    to-monitoring  = { src = [var.network_cidr], tags = ["monitoring"], ports = ["10051", "514"] }
    bastion-to-ui  = { src = ["${local.host_ip.bastion}/32"], tags = ["monitoring", "mq"], ports = ["80", "15672"] }
  }
}

resource "google_compute_firewall" "allow" {
  for_each      = local.firewall
  name          = "p2-allow-${each.key}"
  network       = google_compute_network.main.id
  direction     = "INGRESS"
  priority      = 1000
  source_ranges = each.value.src
  target_tags   = each.value.tags
  allow {
    protocol = "tcp"
    ports    = each.value.ports
  }
  log_config {
    metadata = "EXCLUDE_ALL_METADATA"
  }
}

# --- DNS interne : noms de service stables (les VIP) et noms des serveurs ---------------------------------
resource "google_dns_managed_zone" "internal" {
  name        = "p2-internal"
  dns_name    = "p2.genarchi.internal."
  description = "Noms internes de la P2"
  visibility  = "private"
  private_visibility_config {
    networks {
      network_url = google_compute_network.main.id
    }
  }
}

resource "google_dns_record_set" "service" {
  for_each     = { db = local.db_vip, nas = local.nas_vip }
  managed_zone = google_dns_managed_zone.internal.name
  name         = "${each.key}.${google_dns_managed_zone.internal.dns_name}"
  type         = "A"
  ttl          = 60
  rrdatas      = [each.value]
}

resource "google_dns_record_set" "host" {
  for_each     = local.host_ip
  managed_zone = google_dns_managed_zone.internal.name
  name         = "${each.key}.${google_dns_managed_zone.internal.dns_name}"
  type         = "A"
  ttl          = 300
  rrdatas      = [each.value]
}
