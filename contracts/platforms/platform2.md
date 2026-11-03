# Contrat Platform 2 — « Datacenter virtuel »

Contrat `0.1.0`, **proposition non validée** (fournisseur : [ADR 0001](../../docs/adr/0001-fournisseur-gcp.md), proposé). Les seuils sont des cibles proposées, à confirmer avec Q-001. Ce que la Platform 2 promet à l'app, aux tests et au jury. Le *comment* est dans [`docs/architecture/platform2.md`](../../docs/architecture/platform2.md).

## 1. Positionnement

Colonne **« Virtual 2 Virtual / DC as a Service »** du cours (Cours 1, slide 10) : GCP est utilisé comme un datacenter d'entreprise virtualisé, **sans transformation applicative**. Haute disponibilité par **redondance de l'infrastructure**, exploitation **ITIL** (procédures humaines).

## 2. Engagements de service (cibles, vérifiées par `contracts/tests/acceptance.md`)

| Indicateur | Cible P2 | Remarque |
|---|---|---|
| Modèle SLA | *Designed for failover* | Cours 1, slide 9 |
| Disponibilité | 99,9 % (cible de conception, non mesurable sur un mois de TD) | Mesurée pendant les campagnes T1–T5 |
| Latence `GET /events` | p95 < 300 ms à 50 req/s | Au-delà, saturation attendue (scalabilité verticale) |
| Capacité d'achat | ≥ 50 commandes/s soutenues | Limite assumée, à mesurer en T1 |
| Délai d'émission des billets (I4) | ≤ 15 min (batch) + durée du batch | Billet `pending` visible tout de suite |
| Perte d'une VM web ou app | Aucune requête perdue au-delà de ~10 s (retrait par health check) | Remise en service **manuelle** |
| Perte de la base primaire | **RTO ≤ 30 min**, **RPO ≤ 5 min** | Bascule manuelle par runbook `ops/runbooks/p2-db-failover.md` |
| Perte d'une zone | RTO ≤ 30 min (zone b survit si la base y est promue), RPO ≤ 5 min | Le partage NFS (zone a) est un SPOF assumé : les QR sont régénérables |
| Sauvegarde | `pg_dump` quotidien 02:00 (rétention 7 j) + snapshots de disques quotidiens (rétention 7 j) | Restauration = runbook |
| Mise en production | Fenêtre de maintenance, déploiement VM par VM, après RFC approuvée | Pas de rollback automatique |
| Patching | Mensuel, en place (`apt upgrade`), VM par VM | Dérive de configuration possible et assumée |

## 3. Ce que la plateforme fournit à l'app

Voir la colonne P2 de [`runtime/app-runtime.md` § B](../runtime/app-runtime.md#b-ce-que-chaque-plateforme-doit-fournir). En résumé : VM Debian 12, Python 3.11, virtualenv + systemd, PostgreSQL 15, partage NFS sur `/mnt/tickets`, fichier d'environnement `/etc/genarchi/genarchi.env`, timer d'émission toutes les 15 min.

## 4. Contraintes de génération (non négociables)

La P2 **ne doit pas** utiliser :

- de container (ni Docker sur VM, ni Cloud Run, ni GKE) ;
- de service de données managé (Cloud SQL, AlloyDB, Firestore, Memorystore…) ;
- d'autoscaling ni d'autohealing (pas de Managed Instance Group) ;
- de stockage objet pour les données de l'app (pas de bucket Cloud Storage) ;
- de bus d'événements (Pub/Sub, Eventarc) ;
- de load balancer global (anycast multi-région).

Ces interdits sont vérifiés en CI à partir de [`boundary.toml`](boundary.toml). Exception : le bucket de state Terraform, créé par `infra/bootstrap/`, hors périmètre plateforme.

Autorisé et attendu : VM nommées, disques persistants, VPC custom avec sous-réseaux /24 par tier, règles firewall par plage, DNS privé (Cloud DNS) pour le nom `db-primary`, load balancer **régional**, Cloud NAT pour les mises à jour, bastion.

## 5. Interface Terraform (`infra/p2/`)

### Entrées

| Variable | Type | Défaut | Rôle |
|---|---|---|---|
| `project_id` | string | — | Projet GCP dédié P2 |
| `region` | string | `europe-west9` | Région unique |
| `zones` | list(string) | `["europe-west9-a", "europe-west9-b"]` | Les deux « DC » |
| `name_prefix` | string | `p2` | Préfixe des ressources |
| `vpc_cidr_plan` | object | voir archi | Plages des sous-réseaux front, app, data, admin, proxy-only |
| `machine_types` | map(string) | `web=e2-small, app=e2-small, db=e2-medium, nfs=e2-small, batch=e2-small, mon=e2-medium, bastion=e2-micro` | Dimensionnement **vertical** |
| `os_image` | string | `debian-cloud/debian-12` | Image de base |
| `db_disk_size_gb` | number | `20` | Disque de données PostgreSQL |
| `admin_members` | list(string) | — | Comptes autorisés en SSH via IAP sur le bastion |
| `alert_webhook_url` | string (sensible) | — | Webhook Discord des alertes Zabbix, fourni hors dépôt |
| `labels` | map(string) | `{ platform = "p2", project = "genarchi" }` | Appliqués partout |

### Sorties

| Sortie | Contenu |
|---|---|
| `base_url` | URL publique (LB régional) |
| `lb_ip` | IP du load balancer |
| `instances` | map nom → `{ zone, internal_ip, role }` |
| `ansible_inventory` | Inventaire INI généré, consommé par `infra/p2/ansible/` |
| `db_primary_fqdn` | `db-primary.p2.genarchi.internal` |
| `bastion_name` | Nom du bastion (pour `gcloud compute ssh --tunnel-through-iap`) |

### Cycle de vie

`terraform apply` construit le « datacenter » (réseau, VM, LB, DNS, snapshots planifiés). **Ensuite** Ansible installe et configure (nginx, app, PostgreSQL + réplication, NFS, Zabbix, timers). Le temps total jusqu'au premier billet vendu est mesuré en T8.
