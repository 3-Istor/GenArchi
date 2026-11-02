# Spec d'architecture — Platform 2 « Datacenter virtuel »

> **Statut : à challenger** (voir [`challenge.md`](challenge.md)). Spec texte d'abord, schémas Noodle ensuite.
> Contrat associé : [`contracts/platforms/platform2.md`](../../contracts/platforms/platform2.md).
> Les IDs (`p2-…`) sont stables : ce sont ceux du futur `architecture/p2/model.yaml` Noodle.

## 1. Principe

Un datacenter d'entreprise des années 2010 reconstruit dans GCP : **deux zones = deux salles (« DC 1 » et « DC 2 ») d'un même campus**, architecture 3 tiers (Présentation / Application / Données), serveurs nommés, middleware installé dans les VM, haute dispo par **redondance**, bascules et exploitation **manuelles** selon des procédures écrites.

Construit par Terraform (livrable imposé) + Ansible (installation initiale). **Après la construction, plus aucune automatisation** : toute action de run est un runbook exécuté par un humain.

## 2. Zones (régions et groupes Noodle)

| ID | Kind | Titre | Sous-titre | Contient |
|---|---|---|---|---|
| `p2-internet` | region | INTERNET | — | `p2-user`, `p2-operator` |
| `p2-gcp` | region | GCP PROJECT GENARCHI-P2 | europe-west9 (Paris) | tout le reste |
| `p2-edge` | group | NETWORK EDGE | équipements réseau managés | `p2-lb`, `p2-nat` |
| `p2-vpc` | region | VPC P2-VPC | 10.20.0.0/16 | les deux DC |
| `p2-dc1` | region | DC 1 | zone europe-west9-a | VM de la zone a |
| `p2-dc2` | region | DC 2 | zone europe-west9-b | VM de la zone b |
| `p2-svc` | group | IP SERVICES | Cloud DNS privé | `p2-dns` |
| `p2-tooling` | group | BUILD | hors run | `p2-terraform`, `p2-ansible` |

## 3. Plan réseau

Sur GCP un sous-réseau est **régional** (il couvre les deux zones). On garde un sous-réseau /24 par tier, comme les VLAN d'un DC ; la séparation DC 1 / DC 2 est portée par la zone.

| Sous-réseau | CIDR | Rôle |
|---|---|---|
| `p2-front` | 10.20.1.0/24 | Présentation (nginx) |
| `p2-app` | 10.20.2.0/24 | Application + batch |
| `p2-data` | 10.20.3.0/24 | PostgreSQL + NFS |
| `p2-admin` | 10.20.9.0/24 | Bastion + supervision |
| `p2-proxy-only` | 10.20.64.0/23 | Réservé au load balancer régional (proxies Envoy managés) |

Aucune VM n'a d'IP publique. Sortie internet (paquets `apt`) par **Cloud NAT**.

### Matrice de flux (règles firewall VPC)

En P2, les règles sont écrites **par plage d'IP de sous-réseau** (style ACL de DC), pas par identité ni par tag : c'est une différence volontaire avec la P3.

| # | Source | Destination | Port | Rôle |
|---|---|---|---|---|
| F1 | 10.20.64.0/23 + 35.191.0.0/16 + 130.211.0.0/22 | `p2-front` | TCP 80 | LB et health checks → nginx |
| F2 | `p2-front` | `p2-app` | TCP 8080 | nginx → app |
| F3 | `p2-app` | `p2-data` | TCP 5432 | app et batch → PostgreSQL |
| F4 | `p2-data` | `p2-data` | TCP 5432 | réplication db-02 → db-01 |
| F5 | `p2-app` | `p2-data` | TCP 2049 | app et batch → NFS v4 |
| F6 | `p2-admin` | tous | TCP 10050 | Zabbix server → agents (pull) |
| F7 | tous | `p2-admin` | TCP 10051 | agents → Zabbix server (active checks) |
| F8 | 35.235.240.0/20 | `p2-bastion` | TCP 22 | tunnel IAP → bastion |
| F9 | `p2-bastion` | tous | TCP 22 | rebond SSH d'administration |
| F10 | tout le reste | — | — | **refusé** (règle par défaut, journalisée) |

Flux explicitement interdits à dessiner (`denied: true`, `enforced_by: p2-firewall`) : `p2-web-*` → `p2-db-*` (5432), `p2-user` → `p2-app-*` (8080).

## 4. Inventaire des composants

| ID | Titre | Tech | Kind | Zone | Sous-réseau / IP | Type machine | Ports (écoute) | Rôle |
|---|---|---|---|---|---|---|---|---|
| `p2-user` | Acheteur | navigateur | external (actor) | internet | — | — | — | Achète et télécharge ses billets |
| `p2-operator` | Opérateur (N2) | gcloud + SSH | external (actor) | internet | — | — | — | Exécute les runbooks |
| `p2-lb` | Load balancer régional | Regional external Application LB | cloud | edge | IP publique régionale | managé | `http` TCP 80 (`https` 443 si domaine) | Point d'entrée, health check `/readyz`, répartit sur les 2 DC |
| `p2-nat` | Passerelle internet | Cloud NAT + Cloud Router | cloud | edge | — | managé | — | Sortie pour les mises à jour |
| `p2-web-01` | web-01 | nginx · Debian 12 | frontend | DC 1 | front · 10.20.1.11 | e2-small | `http` TCP 80 | Reverse proxy vers `app-01` et `app-02`, sert le front statique |
| `p2-web-02` | web-02 | nginx · Debian 12 | frontend | DC 2 | front · 10.20.1.12 | e2-small | `http` TCP 80 | Idem |
| `p2-app-01` | app-01 | API Python · systemd | backend | DC 1 | app · 10.20.2.11 | e2-small | `api` TCP 8080 | Serveur d'application (`serve-api`) |
| `p2-app-02` | app-02 | API Python · systemd | backend | DC 2 | app · 10.20.2.12 | e2-small | `api` TCP 8080 | Idem |
| `p2-batch-01` | batch-01 | systemd timers | backend | DC 2 | app · 10.20.2.21 | e2-small | — | « Nuit batch » : `issue-pending` /15 min, `pg_dump` 02:00, export CSV 03:00 |
| `p2-db-01` | db-01 | PostgreSQL 15 · primaire | database (cylinder) | DC 1 | data · 10.20.3.11 | e2-medium + disque 20 Go | `pg` TCP 5432 | Base primaire |
| `p2-db-02` | db-02 | PostgreSQL 15 · réplique | database (cylinder) | DC 2 | data · 10.20.3.12 | e2-medium + disque 20 Go | `pg` TCP 5432 | Réplique streaming asynchrone, lecture seule |
| `p2-nfs-01` | nfs-01 | NFS v4 · Debian 12 | database (cylinder) | DC 1 | data · 10.20.3.21 | e2-small + disque 20 Go | `nfs` TCP 2049 | Partage `/srv/tickets` (QR) et `/srv/exports` (CSV) |
| `p2-mon-01` | mon-01 | Zabbix 7 server + PostgreSQL local | tool | DC 1 | admin · 10.20.9.11 | e2-medium | `zbx-trapper` TCP 10051 | Supervision, alertes mail |
| `p2-bastion` | bastion | OpenSSH · Debian 12 | security | DC 1 | admin · 10.20.9.10 | e2-micro | `ssh` TCP 22 | Seul point d'entrée d'administration |
| `p2-dns` | Zone privée `p2.genarchi.internal` | Cloud DNS | cloud | IP services | — | managé | — | `db-primary` → IP de la base primaire, `nfs` → nfs-01 |
| `p2-firewall` | Règles firewall VPC | VPC firewall | security | VPC | — | — | — | Applique la matrice de flux |
| `p2-snapshots` | Snapshots planifiés | resource policy | tool | gcp | — | — | — | Snapshots quotidiens des disques `db-*` et `nfs-01`, rétention 7 j |
| `p2-terraform` | Terraform | `infra/p2` | tool | build | — | — | — | Construit le DC |
| `p2-ansible` | Ansible | `infra/p2/ansible` | tool | build | — | — | — | Installe et configure (via bastion) |

Agents Zabbix (`zbx-agent` TCP 10050) sur chaque VM : à dessiner comme port des VM, pas comme boîte.

## 5. Connexions

Sens = celui qui ouvre la connexion → celui qui écoute (règle Noodle).

| ID | De | Vers | Port | Verbe · protocole | Kind |
|---|---|---|---|---|---|
| `c-user-lb` | `p2-user` | `p2-lb` | http | buy · HTTP(S) | flow |
| `c-lb-web01` / `c-lb-web02` | `p2-lb` | `p2-web-0x` | http | proxy · HTTP | flow |
| `c-web-app` | `p2-web-0x` | `p2-app-0x` (les deux, upstream nginx) | api | proxy · HTTP | flow |
| `c-app-db` | `p2-app-0x` | `p2-db-01` (via `db-primary`) | pg | transaction · PostgreSQL | flow |
| `c-app-nfs` | `p2-app-0x` | `p2-nfs-01` | nfs | read QR · NFS | flow |
| `c-batch-db` | `p2-batch-01` | `p2-db-01` | pg | read pending, pg_dump · PostgreSQL | async |
| `c-batch-nfs` | `p2-batch-01` | `p2-nfs-01` | nfs | write QR, CSV · NFS | async |
| `c-db02-db01` | `p2-db-02` | `p2-db-01` | pg | stream WAL · PostgreSQL replication | async |
| `c-mon-agents` | `p2-mon-01` | toutes les VM | zbx-agent | poll · Zabbix | async |
| `c-agents-mon` | toutes les VM | `p2-mon-01` | zbx-trapper | push alerts · Zabbix | async |
| `c-op-bastion` | `p2-operator` | `p2-bastion` | ssh | admin · SSH via IAP | flow |
| `c-bastion-vms` | `p2-bastion` | toutes les VM | ssh | admin · SSH | flow |
| `c-vms-nat` | toutes les VM | `p2-nat` | — | apt · HTTPS | async |
| `c-web-db-denied` | `p2-web-0x` | `p2-db-01` | pg | — | flow, **denied**, `enforced_by: p2-firewall` |

Références (configuration, pas du trafic) : `p2-app-0x` → `p2-dns` (résout `db-primary`) ; `p2-snapshots` → disques `db-*`, `nfs-01` ; `p2-ansible` → toutes les VM (config) ; `/etc/genarchi/genarchi.env` (`envFrom`).

## 6. Flux à numéroter

### Vue `p2-topology` — « Comment un achat traverse le datacenter virtuel, et qu'est-ce qui le protège ? »

Chemin nominal (data plane) :
1. `c-user-lb` — l'acheteur poste sa commande
2. `c-lb-web01` — le LB choisit un nginx sain
3. `c-web-app` — nginx relaie vers un serveur d'application
4. `c-app-db` — transaction SQL : stock décrémenté, commande + billets `pending`

Arrière-plan (control plane) :
- A. `c-batch-db` + `c-batch-nfs` — toutes les 15 min, émission des QR sur le partage
- B. `c-db02-db01` — réplication continue vers DC 2
- C. `c-mon-agents` / `c-agents-mon` — supervision
- D. 02:00 `pg_dump`, 03:00 export CSV des ventes (« échange par fichier »)

Note sur `p2-db-01` : « En cas de panne : runbook `p2-db-failover`, bascule manuelle (RTO ≤ 30 min) ».

### Vue `p2-db-failover` (sequence) — « Que fait l'opérateur quand db-01 tombe ? »

1. Zabbix détecte `db-01` injoignable → mail à l'astreinte
2. L'opérateur ouvre un ticket incident, se connecte au bastion (IAP)
3. Vérifie que `db-01` est bien mort (éviter le split-brain) et l'arrête
4. `pg_ctl promote` sur `db-02`
5. Met à jour l'enregistrement DNS `db-primary` → 10.20.3.12
6. Redémarre l'API sur `app-01` et `app-02` (nouvelle connexion)
7. Vérifie `/readyz`, ferme l'incident, planifie la reconstruction d'une réplique (problème ITIL)

### Vue `p2-ticket-download` (optionnelle)

`c-user-lb` → `c-lb-web0x` → `c-web-app` → `c-app-nfs` : le QR est lu sur le partage NFS et renvoyé par l'API.

## 7. Modes de défaillance

| Panne | Effet | Détection | Reprise | Type |
|---|---|---|---|---|
| `web-0x` ou `app-0x` | Retiré du LB en ~10 s | Health check + Zabbix | Relance manuelle | Redondance |
| `db-01` | Achats en erreur | Zabbix | Runbook bascule, RTO ≤ 30 min, RPO ≤ 5 min | Redondance + DRP manuel |
| `db-02` | Aucun impact immédiat, plus de protection | Zabbix (lag) | Reconstruire la réplique | — |
| `nfs-01` | QR non téléchargeables, émission bloquée | Zabbix | Restauration du snapshot ; les QR se régénèrent depuis la base | **SPOF assumé** |
| `batch-01` | Billets restent `pending` | Zabbix + âge des `pending` | Relance manuelle | **SPOF assumé** |
| `mon-01` | Plus d'alerte | — (personne ne surveille le superviseur) | Manuel | Limite P2 à citer en soutenance |
| Zone a entière | DC 1 perdu : db primaire, nfs, mon, bastion | LB + Zabbix (si encore vivant) | Runbook DR : promotion db-02, recréation nfs depuis snapshot, bastion en zone b | DRP manuel |
| Pic de charge | Saturation à la taille des VM | Latence | Resize vertical = arrêt/redémarrage VM par VM | Scalabilité verticale |

## 8. Exploitation (ITIL)

| Activité | P2 |
|---|---|
| Changement | Issue GitHub « Demande de changement » (RFC) + approbation d'un autre membre avant tout `terraform apply` ou runbook de mise en prod |
| Incident | Issue « Incident », runbook, post-mortem si RTO dépassé |
| Runbooks à écrire (`ops/runbooks/`) | `p2-deploy`, `p2-db-failover`, `p2-db-rebuild-replica`, `p2-restore-dump`, `p2-patch`, `p2-zone-dr`, `p2-resize` |
| Sauvegarde | Contrôle quotidien du rapport `pg_dump` (un humain le lit) |
| Secrets | Ansible Vault, mot de passe partagé hors repo |

## 9. Coût indicatif (24/7)

10 VM (≈ 60–110 $/mois) + LB (≈ 20 $) + disques et snapshots (≈ 10 $) + NAT (≈ 5 $). **Arrêter ou détruire en dehors des séances.**

## 10. Pour Noodle

Vues proposées : `p2-topology` (topology), `p2-db-failover` (sequence), `p2-network` (topology centrée firewall, avec les flux interdits), et une vue `landscape` commune P2/P3 si utile.
Icônes manquantes à ajouter dans `.noodle/icons/` : `gcp`, `debian`, `nginx`, `postgresql`, `zabbix`, `ansible`, `nfs` (générique). Disponibles : `rack`, `globe`, `user`, `python`, `fastapi`, `terraform`.
Mapping kinds : nginx = frontend (cyan), app = backend (emerald), PostgreSQL/NFS = database (violet), LB/NAT/DNS = cloud (amber), bastion/firewall = security (rose), Zabbix/Terraform/Ansible = tool (slate).
