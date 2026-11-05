# Contrat Platform 2 — « Datacenter virtuel »

Contrat `0.2.0`, **proposition non validée** ([ADR 0015](../../docs/adr/0015-p2-clusters-etat-de-l-art.md)). Fournisseur : GCP ([ADR 0001](../../docs/adr/0001-fournisseur-gcp.md), accepté). Ce que la P2 promet à l'app, aux tests et au jury. Le *comment* : [`docs/architecture/platform2.md`](../../docs/architecture/platform2.md) et [`infra/p2/`](../../infra/p2/README.md).

## 1. Positionnement

Colonne « Virtual 2 Virtual / DC as a Service » (cours 1, diapositive 10) : GCP est utilisé comme un datacenter d'entreprise, **sans transformation de l'application**. Haute disponibilité par **redondance de l'infrastructure** (clusters installés dans des VM), exploitation par **procédures humaines** ([runbooks](../../docs/runbooks/README.md)).

## 2. Engagements de service (cibles)

| Indicateur | Cible P2 | Mécanisme |
|---|---|---|
| Modèle SLA | *Designed for failover* | Cours 1, diapositive 9 |
| Délai d'émission des billets (I4) | quelques secondes ; ≤ 5 min en dégradé | File RabbitMQ ; rattrapage toutes les 5 min |
| Perte d'un serveur web ou d'app | ≤ 10 s de rotation, remise en service manuelle | Health checks du LB et d'Apache |
| Perte du primaire PostgreSQL | RTO < 1 min (automatique), **RPO = 0** | Patroni, réplication synchrone, quorum etcd |
| Perte d'un nœud RabbitMQ | aucune interruption | Files quorum, 3 nœuds |
| Perte du NAS actif | RTO ≤ 15 min (runbook), **RPO = 0** | Disque régional, bascule manuelle |
| Perte d'une zone (DC) | Service maintenu ; NAS à basculer à la main | Tout est doublé en DC1 / DC2, témoins en zone c |
| Perte de la région | Hors engagement : PRA manuel | Instantanés copiés dans l'UE, sauvegardes Barman |
| Sauvegarde | WAL en continu + complète nocturne (7 j), instantanés horaires du NAS et nocturnes des disques (7 j) | Barman, politiques d'instantanés |
| Mise en production | RFC, déploiement serveur par serveur, retour arrière = version précédente | `make p2-release` |
| Patching | Mensuel, serveur par serveur | [`p2-deploy.md`](../../docs/runbooks/p2-deploy.md) |

## 3. Ce que la plateforme fournit à l'app

Colonne P2 de [`runtime/app-runtime.md` § B](../runtime/app-runtime.md#b-ce-que-chaque-plateforme-doit-fournir) : VM Debian 13, Python 3.13, virtualenv + systemd, PostgreSQL 17 via `db.p2.genarchi.internal`, NFS sur `/mnt/tickets`, RabbitMQ (`AMQP_URLS`), `/etc/genarchi/genarchi.env` (0600).

## 4. Contraintes de génération

La P2 **ne doit pas** utiliser : container, service de données managé, autoscaling ou autohealing, stockage objet pour les données de l'app, bus d'événements managé, load balancer global. Vérifié par [`boundary.toml`](boundary.toml) (`scripts/check_boundary.py`). Exception : le bucket d'état OpenTofu (`infra/bootstrap/`), hors plateforme.

Autorisé : VM nommées, disques (zonaux et régionaux), VPC à sous-réseaux par tier, pare-feu par plage, DNS privé, LB **régionaux** (externe et internes), Certificate Manager, Cloud NAT, IAP pour le bastion.

## 5. Interface OpenTofu (`infra/p2/`)

Entrées principales : `project_id`, `region` (`europe-west9`), `domain`, `cloudflare_zone_id`, `network_cidr` (`10.20.0.0/16`), `nas_active` (`nas-1` | `nas-2`), `machine_types`, `image` (`debian-cloud/debian-13`), `labels`. Détail : [`variables.tf`](../../infra/p2/variables.tf).

Sorties : `url`, `lb_ip`, `bastion`, `network_prefix`, `nas_active`, `ansible_inventory` (sensible : contient les secrets, écrit par `make p2-inventory`).

Cycle de vie : `make p2-apply` construit le datacenter, `make p2-configure` (Ansible) installe et configure tout, `make p2-release` met une version en production.
