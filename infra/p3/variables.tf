variable "project_id" {
  description = "Projet GCP de la Platform 3"
  type        = string
}

variable "regions" {
  description = "Régions Cloud Run actives (au moins deux). Alignées sur les réplicas de Firestore eur3."
  type        = list(string)
  default     = ["europe-west1", "europe-west4"]
  validation {
    condition     = length(var.regions) >= 2
    error_message = "La P3 exige au moins deux régions actives."
  }
}

variable "firestore_location" {
  description = "Emplacement multi-région de Firestore"
  type        = string
  default     = "eur3"
}

variable "storage_regions" {
  description = "Deux régions du bucket dual-région des QR"
  type        = list(string)
  default     = ["EUROPE-WEST1", "EUROPE-WEST4"]
}

variable "name_prefix" {
  type    = string
  default = "p3"
}

variable "domain" {
  description = "Nom public de la P3 (enregistrement créé dans Cloudflare)"
  type        = string
  default     = "p3.genarchi.3istor.com"
}

variable "cloudflare_zone_id" {
  description = "Zone Cloudflare de 3istor.com (lue dans le dépôt 3-Istor/K3s)"
  type        = string
  default     = "5984eff5179d6656a7c9e1b00c768d21"
}

variable "app_image" {
  description = "Image de l'application (Artifact Registry, de préférence par digest). Vide : image publique de démonstration."
  type        = string
  default     = ""
}

variable "app_version" {
  type    = string
  default = "dev"
}

variable "min_instances" {
  description = "Instances minimales de l'API par région. >= 1 : requis par Cloud Run service health pour la bascule"
  type        = number
  default     = 1
  validation {
    condition     = var.min_instances >= 1
    error_message = "service health a besoin d'au moins une instance par région."
  }
}

variable "max_instances" {
  description = "Plafond par région et par service : protège la facture (denial of wallet)"
  type        = number
  default     = 20
}

variable "chaos_enabled" {
  description = "Hooks de chaos de l'app (/internal/chaos) et test de panne nocturne"
  type        = bool
  default     = true
}

variable "chaos_schedule" {
  description = "Planification du test de panne de région (cron, Europe/Paris)"
  type        = string
  default     = "17 3 * * *"
}

variable "chaos_unready_regions" {
  description = "Régions dont l'API répond 503 à /readyz (rempli par le test de panne ou `make p3-chaos-region`)"
  type        = list(string)
  default     = []
}

variable "alert_email" {
  description = "Adresse qui reçoit les alertes SLO (vide : aucune notification)"
  type        = string
  default     = ""
}

variable "labels" {
  type    = map(string)
  default = { platform = "p3", project = "genarchi" }
}
