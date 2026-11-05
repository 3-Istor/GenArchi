variable "project_id" {
  description = "Projet GCP de la Platform 2"
  type        = string
}

variable "region" {
  description = "Région unique de la P2 : ses zones a et b jouent les deux datacenters, la zone c le site témoin"
  type        = string
  default     = "europe-west9"
}

variable "domain" {
  description = "Nom public de la P2 (enregistrement créé dans Cloudflare)"
  type        = string
  default     = "p2.genarchi.3istor.com"
}

variable "cloudflare_zone_id" {
  description = "Zone Cloudflare de 3istor.com (lue dans le dépôt 3-Istor/K3s)"
  type        = string
  default     = "5984eff5179d6656a7c9e1b00c768d21"
}

variable "network_cidr" {
  description = "Plan d'adressage : un /24 par tier est découpé dans ce /16"
  type        = string
  default     = "10.20.0.0/16"
}

variable "nas_active" {
  description = "Serveur NAS qui porte le disque régional. Le runbook de bascule le passe à nas-2 (et inversement)."
  type        = string
  default     = "nas-1"
  validation {
    condition     = contains(["nas-1", "nas-2"], var.nas_active)
    error_message = "nas_active vaut nas-1 ou nas-2."
  }
}

variable "machine_types" {
  description = "Gabarit par rôle ; surcharger pour réduire le coût hors soutenance"
  type        = map(string)
  default = {
    bastion    = "e2-micro"
    rp         = "e2-small"
    app        = "e2-small"
    scheduler  = "e2-small"
    db         = "e2-medium"
    witness    = "e2-small"
    mq         = "e2-small"
    nas        = "e2-small"
    backup     = "e2-small"
    monitoring = "e2-medium"
  }
}

variable "image" {
  description = "Image des VM (même OS partout)"
  type        = string
  default     = "debian-cloud/debian-13"
}

variable "labels" {
  type    = map(string)
  default = { platform = "p2", project = "genarchi" }
}
