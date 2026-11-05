provider "google" {
  project               = var.project_id
  region                = var.region
  default_labels        = var.labels
  user_project_override = true
  billing_project       = var.project_id
}

# Jeton lu dans CLOUDFLARE_API_TOKEN (droit « DNS edit » sur la zone 3istor.com).
provider "cloudflare" {}

resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com", "dns.googleapis.com", "certificatemanager.googleapis.com",
    "iap.googleapis.com", "oslogin.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# Accès SSH par comptes Google (OS Login) : aucune clé posée à la main sur les VM.
resource "google_compute_project_metadata_item" "oslogin" {
  key        = "enable-oslogin"
  value      = "TRUE"
  depends_on = [google_project_service.apis]
}

locals {
  zone = { for z in ["a", "b", "c"] : z => "${var.region}-${z}" }

  # Un /24 par tier, comme les VLAN d'un datacenter. Les zones a et b partagent ces sous-réseaux régionaux.
  subnets = {
    dmz  = cidrsubnet(var.network_cidr, 8, 0) # reverse proxies
    app  = cidrsubnet(var.network_cidr, 8, 1) # serveurs d'application, ordonnanceur
    data = cidrsubnet(var.network_cidr, 8, 2) # PostgreSQL, etcd, RabbitMQ, NAS
    mgmt = cidrsubnet(var.network_cidr, 8, 3) # bastion, supervision, sauvegarde
  }
  proxy_only_cidr = cidrsubnet(var.network_cidr, 8, 255)

  # Inventaire des serveurs : nom → zone (a = DC1, b = DC2, c = site témoin), tier, adresse fixe, groupes Ansible.
  hosts = {
    bastion    = { zone = "c", subnet = "mgmt", ip = 5, role = "bastion", groups = ["bastions"] }
    monitoring = { zone = "c", subnet = "mgmt", ip = 10, role = "monitoring", groups = ["zabbix"] }
    backup     = { zone = "c", subnet = "mgmt", ip = 11, role = "backup", groups = ["barman"] }
    rp-1       = { zone = "a", subnet = "dmz", ip = 11, role = "rp", groups = ["reverse_proxy"] }
    rp-2       = { zone = "b", subnet = "dmz", ip = 21, role = "rp", groups = ["reverse_proxy"] }
    app-1a     = { zone = "a", subnet = "app", ip = 11, role = "app", groups = ["app"] }
    app-2a     = { zone = "a", subnet = "app", ip = 12, role = "app", groups = ["app"] }
    app-1b     = { zone = "b", subnet = "app", ip = 21, role = "app", groups = ["app"] }
    app-2b     = { zone = "b", subnet = "app", ip = 22, role = "app", groups = ["app"] }
    scheduler  = { zone = "a", subnet = "app", ip = 30, role = "scheduler", groups = ["schedulers"] }
    db-1       = { zone = "a", subnet = "data", ip = 11, role = "db", groups = ["db", "etcd"] }
    db-2       = { zone = "b", subnet = "data", ip = 21, role = "db", groups = ["db", "etcd"] }
    witness    = { zone = "c", subnet = "data", ip = 31, role = "witness", groups = ["etcd", "rabbitmq", "quorum_witness"] }
    mq-1       = { zone = "a", subnet = "data", ip = 12, role = "mq", groups = ["rabbitmq"] }
    mq-2       = { zone = "b", subnet = "data", ip = 22, role = "mq", groups = ["rabbitmq"] }
    nas-1      = { zone = "a", subnet = "data", ip = 13, role = "nas", groups = ["nas"] }
    nas-2      = { zone = "b", subnet = "data", ip = 23, role = "nas", groups = ["nas"] }
  }
  host_ip = { for name, h in local.hosts : name => cidrhost(local.subnets[h.subnet], h.ip) }

  # IP virtuelles portées par des load balancers internes (le VPC ignore l'ARP gratuit : pas de keepalived).
  db_vip  = cidrhost(local.subnets.data, 5)
  nas_vip = cidrhost(local.subnets.data, 6)

  # Disques de données (en plus du disque système), montés par Ansible.
  data_disks = {
    db-1   = { size = 20, mount = "/var/lib/postgresql" }
    db-2   = { size = 20, mount = "/var/lib/postgresql" }
    backup = { size = 50, mount = "/var/lib/barman" }
  }

  gcp_health_check_ranges = ["35.191.0.0/16", "130.211.0.0/22"]
  iap_range               = "35.235.240.0/20"
}
