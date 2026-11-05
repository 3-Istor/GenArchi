output "url" {
  value = "https://${var.domain}"
}

output "lb_ip" {
  value = google_compute_address.lb.address
}

output "bastion" {
  value = { name = "bastion", zone = google_compute_instance.host["bastion"].zone }
}

output "network_prefix" {
  description = "Préfixe des adresses internes (motif Host de ssh_config)"
  value       = join(".", slice(split(".", var.network_cidr), 0, 2))
}

output "nas_active" {
  value = var.nas_active
}

output "ansible_inventory" {
  description = "Inventaire Ansible (contient des secrets) : écrit par `make p2-inventory`"
  sensitive   = true
  value = yamlencode({
    all = {
      vars = {
        gcp_project     = var.project_id
        gcp_region      = var.region
        public_domain   = var.domain
        network_cidr    = var.network_cidr
        subnets         = local.subnets
        proxy_only_cidr = local.proxy_only_cidr
        internal_domain = trimsuffix(google_dns_managed_zone.internal.dns_name, ".")
        db_vip          = local.db_vip
        nas_vip         = local.nas_vip
        nas_active      = var.nas_active
        p2_hosts        = local.host_ip
        secrets         = { for k, v in random_password.secret : k => v.result }
      }
      children = {
        for g in distinct(flatten([for h in local.hosts : h.groups])) : g => {
          hosts = {
            for n, h in local.hosts : n => {
              ansible_host = n == "bastion" ? "bastion" : local.host_ip[n]
              gcp_zone     = local.zone[h.zone]
              datacenter   = h.zone == "c" ? "temoin" : "dc${h.zone == "a" ? 1 : 2}"
              data_mount   = try(local.data_disks[n].mount, null)
            } if contains(h.groups, g)
          }
        }
      }
    }
  })
}
