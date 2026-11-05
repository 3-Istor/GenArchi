# Compte de service des VM : aucun rôle. La P2 n'appelle pas les API du cloud depuis ses serveurs.
resource "google_service_account" "vm" {
  account_id   = "p2-servers"
  display_name = "GenArchi P2 VM"
}

resource "google_compute_disk" "data" {
  for_each = local.data_disks
  name     = "${each.key}-data"
  zone     = local.zone[local.hosts[each.key].zone]
  type     = "pd-balanced"
  size     = each.value.size
}

resource "google_compute_instance" "host" {
  for_each     = local.hosts
  name         = each.key
  zone         = local.zone[each.value.zone]
  machine_type = var.machine_types[each.value.role]
  tags         = ["p2", each.value.role]
  labels       = merge(var.labels, { role = each.value.role, dc = each.value.zone == "c" ? "temoin" : "dc${each.value.zone == "a" ? 1 : 2}" })

  boot_disk {
    auto_delete = true
    initialize_params {
      image = var.image
      size  = 20
      type  = "pd-balanced"
    }
  }

  dynamic "attached_disk" {
    for_each = contains(keys(local.data_disks), each.key) ? [google_compute_disk.data[each.key]] : []
    content {
      source      = attached_disk.value.id
      device_name = "data"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.tier[each.value.subnet].id
    network_ip = local.host_ip[each.key]
    # Pas d'access_config : aucune IP publique. Entrée par le LB ou le bastion (IAP), sortie par Cloud NAT.
  }

  service_account {
    email  = google_service_account.vm.email
    scopes = ["cloud-platform"]
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
  }

  metadata = {
    block-project-ssh-keys = "TRUE"
  }

  allow_stopping_for_update = true

  # Le disque régional du NAS est attaché par google_compute_attached_disk (il change de serveur à la bascule).
  lifecycle {
    ignore_changes = [attached_disk]
  }

  depends_on = [google_compute_router_nat.main, google_compute_project_metadata_item.oslogin]
}

# --- NAS actif/passif : disque régional répliqué de façon synchrone entre DC1 et DC2 ----------------------
resource "google_compute_region_disk" "tickets" {
  name          = "nas-tickets"
  region        = var.region
  type          = "pd-balanced"
  size          = 20
  replica_zones = [local.zone.a, local.zone.b]
}

resource "google_compute_attached_disk" "tickets" {
  disk        = google_compute_region_disk.tickets.id
  instance    = google_compute_instance.host[var.nas_active].id
  device_name = "tickets"
}

# --- Instantanés : NAS toutes les heures, disques de données chaque nuit, copiés hors région (UE) -------
resource "google_compute_resource_policy" "snapshots" {
  for_each = { hourly = 1, daily = 24 }
  name     = "p2-snapshots-${each.key}"
  region   = var.region
  snapshot_schedule_policy {
    schedule {
      dynamic "hourly_schedule" {
        for_each = each.value == 1 ? [1] : []
        content {
          hours_in_cycle = 1
          start_time     = "00:00"
        }
      }
      dynamic "daily_schedule" {
        for_each = each.value == 24 ? [1] : []
        content {
          days_in_cycle = 1
          start_time    = "02:00"
        }
      }
    }
    retention_policy {
      max_retention_days    = 7
      on_source_disk_delete = "KEEP_AUTO_SNAPSHOTS"
    }
    snapshot_properties {
      storage_locations = ["eu"]
      guest_flush       = false
      labels            = var.labels
    }
  }
}

resource "google_compute_region_disk_resource_policy_attachment" "tickets" {
  name   = google_compute_resource_policy.snapshots["hourly"].name
  disk   = google_compute_region_disk.tickets.name
  region = var.region
}

resource "google_compute_disk_resource_policy_attachment" "data" {
  for_each = google_compute_disk.data
  name     = google_compute_resource_policy.snapshots["daily"].name
  disk     = each.value.name
  zone     = each.value.zone
}

# --- Groupes d'instances non gérés (un par rôle et par zone) : ce sont les backends des LB -------------
locals {
  instance_groups = {
    for pair in flatten([
      for role in ["rp", "db", "nas"] : [
        for z in ["a", "b"] : { role = role, zone = z, members = [for n, h in local.hosts : n if h.role == role && h.zone == z] }
      ]
    ]) : "${pair.role}-${pair.zone}" => pair
  }
}

resource "google_compute_instance_group" "tier" {
  for_each  = local.instance_groups
  name      = "p2-${each.key}"
  zone      = local.zone[each.value.zone]
  network   = google_compute_network.main.id
  instances = [for n in each.value.members : google_compute_instance.host[n].self_link]

  dynamic "named_port" {
    for_each = each.value.role == "rp" ? [1] : []
    content {
      name = "http"
      port = 80
    }
  }
}
