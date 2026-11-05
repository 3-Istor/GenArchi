# Spec d'architecture — Platform 2 « Datacenter virtuel »

> Version 0.2 (« état de l'art »), **proposée** ([ADR 0015](../adr/0015-p2-clusters-etat-de-l-art.md)). Implémentée dans [`infra/p2/`](../../infra/p2/README.md) ; vérifiée au labo, pas encore sur GCP. Engagements : [contrat P2](../../contracts/platforms/platform2.md).

## 1. Principe

GCP joue un datacenter d'entreprise : des **serveurs nommés**, un réseau découpé en tiers, des **clusters middleware installés dans les VM**. Toute la redondance est dans l'infrastructure ; l'application ne sait rien des pannes. Le *build* est automatisé (OpenTofu crée les machines, Ansible les configure) ; le *run* est humain : alertes Zabbix, puis runbook.

La meilleure P2 possible n'utilise que des composants de génération 2 : pas de base managée, pas de bucket, pas de bus managé, pas d'autoscaling, pas de LB global.

## 2. Sites

| Zone `europe-west9-…` | Rôle | Serveurs |
|---|---|---|
| `a` | **DC1** | `rp-1`, `app-1a`, `app-2a`, `db-1`, `mq-1`, `nas-1`, `scheduler` |
| `b` | **DC2** | `rp-2`, `app-1b`, `app-2b`, `db-2`, `mq-2`, `nas-2` |
| `c` | **Site témoin** (arbitre et exploitation) | `witness` (etcd + RabbitMQ), `bastion`, `monitoring`, `backup` |

Pourquoi un témoin : deux sites ne peuvent pas décider seuls qui a raison après une coupure entre eux (split-brain). Un troisième vote (etcd pour PostgreSQL, troisième nœud RabbitMQ) donne une majorité au site qui reste joignable.

## 3. Réseau

Un VPC `10.20.0.0/16`, un /24 par tier (comme des VLAN), communs aux deux DC :

| Sous-réseau | Plage | Serveurs |
|---|---|---|
| `p2-dmz` | `10.20.0.0/24` | reverse proxies |
| `p2-app` | `10.20.1.0/24` | serveurs d'application, ordonnanceur |
| `p2-data` | `10.20.2.0/24` | PostgreSQL, etcd, RabbitMQ, NAS ; VIP `db` `.5`, VIP `nas` `.6` |
| `p2-mgmt` | `10.20.3.0/24` | bastion, supervision, sauvegarde |
| `p2-proxy-only` | `10.20.255.0/24` | proxys du LB régional (géré par Google) |

Aucune VM n'a d'IP publique. Entrée : le LB (HTTPS) ou le bastion (SSH via IAP). Sortie : Cloud NAT (paquets Debian, PyPI). DNS privé `p2.genarchi.internal` (+ `/etc/hosts` posé par Ansible, pour ne pas dépendre du DNS pendant une panne).

### Flux autorisés (tout le reste est refusé)

| Source | Destination | Port | Pourquoi |
|---|---|---|---|
| IAP `35.235.240.0/20` | bastion | 22 | Administration |
| bastion | toutes les VM | 22 | Administration (ProxyJump) |
| proxy-only, sondes Google | `rp-*` | 80 | LB public → reverse proxies |
| `p2-dmz` | `app-*` | 8080 | Reverse proxies → app |
| `p2-app` | `db-*` | 5432 | App → base (via VIP) |
| `p2-app` | `mq-*`, `witness` | 5672 | App → RabbitMQ |
| `p2-app` | `nas-*` | 2049 | App → NFS (via VIP) |
| sondes Google | `db-*` : 8008, `nas-*` : 2049 | | Health checks des VIP |
| `p2-data` | `db-*`, `witness` | 5432, 8008, 2379-2380 | Réplication, Patroni, etcd |
| `p2-data` | `mq-*`, `witness` | 4369, 25672, 35672-35682 | Cluster RabbitMQ |
| `backup` | `db-*` | 5432, 8008 | Barman |
| `monitoring` | toutes | 10050 | Zabbix (passif) |
| toutes | `monitoring` | 10051, 514 | Zabbix (actif), rsyslog |
| bastion | `monitoring` : 80, `mq-*` : 15672 | | Interfaces web par tunnel SSH |

## 4. Composants

| Composant | Logiciel | Redondance | Bascule |
|---|---|---|---|
| Entrée | LB applicatif externe **régional** + certificat Google (Certificate Manager, autorisation DNS) | Géré, régional | Automatique (health check `/rp-health`) |
| Reverse proxy + WAF | Apache 2.4 + ModSecurity 2 + OWASP CRS 3.3 (`rp-1`, `rp-2`) | 1 par DC | Automatique (LB) |
| Application | `genarchi serve-api` + `genarchi consume`, systemd, virtualenv (4 serveurs) | 2 par DC | Automatique (Apache `mod_proxy_hcheck` sur `/readyz`) |
| Base | PostgreSQL 17 + Patroni 4, réplication **synchrone**, quorum etcd 3.5 (3 membres) | Primaire + réplica synchrone | **Automatique** (Patroni) ; désactivable (`patronictl pause`) |
| IP virtuelle base | LB interne passthrough, sonde `GET :8008/primary` | Gérée | Suit le primaire en ~6 s |
| Messages | RabbitMQ 4.0, 3 nœuds, file **quorum** `tickets.issue` + file de lettres mortes | 3 nœuds (majorité 2) | Automatique (Raft) |
| Fichiers (QR) | NFS v4.2 sur **disque régional** (réplication synchrone a ↔ b) | Actif (`nas-1`) / passif (`nas-2`) | **Manuelle** : `make p2-nas-failover` (force-attach = fencing) |
| IP virtuelle NAS | LB interne passthrough, sonde TCP 2049 | Gérée | Suit le NAS qui sert |
| Rattrapage | Timer systemd `genarchi-issue-pending` (5 min) sur `scheduler` | SPOF assumé (filet) | Recréer la VM |
| Sauvegarde | Barman 3.13 : WAL en continu (slot permanent Patroni) + complète nocturne, PITR 7 j ; instantanés de disques (NAS horaire, données nocturne) copiés dans l'UE | Zone témoin | Runbook de restauration |
| Supervision | Zabbix 7.0 (agents 2 auto-enregistrés, scénario web sur l'URL publique, alertes Discord) | Zone témoin | — |
| Journaux | journald → rsyslog → `monitoring:/var/log/remote/<serveur>/` | File disque côté client | — |
| Accès | Bastion (IAP), OS Login (comptes Google, pas de clé posée à la main) | Zone témoin | — |

## 5. Parcours d'un achat

1. Le navigateur appelle `https://p2.genarchi.3istor.com` : le LB régional termine TLS et choisit `rp-1` ou `rp-2`.
2. ModSecurity filtre la requête ; Apache sert le front statique, ou transmet l'API à un serveur d'app prêt.
3. L'app réserve les places dans PostgreSQL (une transaction, `UPDATE … WHERE remaining >= n`), commit synchrone dans les deux DC.
4. Après commit, l'app publie `ticket.purchased` sur RabbitMQ (confirmations éditeur).
5. Un consommateur (n'importe quel serveur d'app) génère le QR, l'écrit sur le NAS, marque le billet émis.
6. Si l'étape 4 a échoué, le rattrapage émet le billet dans les 5 min.

## 6. Modes de défaillance

| Panne | Effet | Détection | Action | RTO / RPO |
|---|---|---|---|---|
| Serveur d'app | Retiré de la rotation | Apache (10 s), Zabbix | Réparer, relancer | 10 s / 0 |
| Reverse proxy | Retiré par le LB | LB (10 s), Zabbix | Réparer | 10 s / 0 |
| Primaire PostgreSQL | 503 pendant la bascule | Patroni, Zabbix | Vérifier, réintégrer l'ancien primaire ([`p2-db.md`](../runbooks/p2-db.md)) | < 1 min / 0 |
| Nœud RabbitMQ | Aucun | Zabbix | Relancer | 0 / 0 |
| NAS actif | Émission des QR en attente | Zabbix, billets `pending` | [`p2-nas.md`](../runbooks/p2-nas.md) | ≤ 15 min / 0 |
| Zone entière | Moitié de la capacité ; NAS à basculer | Zabbix | [`p2-zone.md`](../runbooks/p2-zone.md) | ≤ 15 min / 0 |
| Erreur humaine (données) | — | — | Restauration Barman à un instant donné | ~30 min / secondes |
| Région | Service arrêté | — | PRA manuel | hors engagement |

Mesures au labo (conteneurs, 2026-11-04) : primaire tué sous 5 achats/s → 43 s de 503, stock cohérent, aucun billet perdu ; nœud RabbitMQ ou serveur d'app tué → aucune erreur client.

## 7. Exploitation

Mise en production par RFC et `make p2-release` (serveur par serveur, `/readyz` attendu avant le suivant, trois versions gardées pour le retour arrière). Patch mensuel serveur par serveur. Tableaux de bord : `make p2-ui`. Détail : [runbooks](../runbooks/README.md).

## 8. Coût indicatif (24/7)

17 VM (1 e2-micro, 13 e2-small, 3 e2-medium), ~470 Go de disques, 1 LB externe et 2 internes, Cloud NAT : de l'ordre de **400 $ par mois**, soit ~14 $ par jour. Ordre de grandeur à vérifier dans le simulateur GCP ; réduire `machine_types` ou arrêter les VM hors séances.

## 9. Écarts avec la v0.1

Base à bascule manuelle et NFS zonal remplacés par Patroni et un disque régional ; batch 15 min remplacé par RabbitMQ ; `pg_dump` remplacé par Barman ; nginx par Apache + ModSecurity ([ADR 0017](../adr/0017-p2-substitutions-outils.md)) ; bastion, supervision et sauvegarde déplacés en zone témoin.
