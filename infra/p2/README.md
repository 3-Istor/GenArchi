# Infrastructure Platform 2 — datacenter virtuel

GCP sert de datacenter : des VM nommées, un réseau découpé en tiers, des clusters middleware installés dans les VM. Build automatisé (OpenTofu + Ansible), exploitation manuelle ([runbooks](../../docs/runbooks/README.md)). Spec : [`docs/architecture/platform2.md`](../../docs/architecture/platform2.md).

```text
Internet ─TLS─▶ LB applicatif régional ─▶ rp-1 (DC1), rp-2 (DC2)      Apache + ModSecurity (CRS)
                                           └─▶ app-1a, app-2a, app-1b, app-2b   API + consommateur RabbitMQ
                    db.p2.genarchi.internal ─▶ db-1 / db-2                PostgreSQL 17 + Patroni (synchrone)
                    nas.p2.genarchi.internal ─▶ nas-1 / nas-2             NFS sur disque régional (actif/passif)
                    mq-1, mq-2, witness                                   RabbitMQ, files quorum
                    etcd : db-1, db-2, witness                            quorum de Patroni
zone c (témoin) :   witness, bastion (IAP), monitoring (Zabbix, rsyslog), backup (Barman)
```

| Fichier | Contenu |
|---|---|
| `main.tf` | Providers, API, **inventaire des serveurs** (zone, tier, adresse fixe, groupes Ansible), plan d'adressage |
| `network.tf` | VPC, sous-réseaux par tier, Cloud NAT, pare-feu (un flux autorisé = une règle, par plage), DNS privé |
| `compute.tf` | VM Debian 13 (Shielded VM, sans IP publique, OS Login), disques de données, disque régional du NAS, instantanés |
| `lb.tf` | LB externe régional + certificat (Certificate Manager, autorisation DNS Cloudflare), IP virtuelles internes (LB passthrough) |
| `secrets.tf` | Secrets générés (dans l'état chiffré du bucket, jamais dans git) |
| `ansible/` | `site.yml` (tout), `app.yml` (mise en production roulante), un rôle par composant |
| `lab/` | Les mêmes rôles sur des conteneurs Debian 13 + systemd (`make p2-lab`) |
| `scripts/` | Génération de l'inventaire et de la config SSH, bascule du NAS |

Cibles : `make p2-plan`, `p2-apply`, `p2-configure`, `p2-release`, `p2-deploy`, `p2-smoke`, `p2-ssh HOST=…`, `p2-ui`, runbooks `p2-db-status`, `p2-db-switchover`, `p2-nas-failover`, `p2-backup-status`. Variables : [`env.mk.example`](env.mk.example), [`variables.tf`](variables.tf).

## Ce qui a été vérifié

- `tofu validate` et `tofu fmt` ; [frontière P2/P3](../../contracts/platforms/boundary.toml) respectée (`scripts/check_boundary.py`).
- **Labo** (`make p2-lab`, 11 conteneurs Debian 13) : `site.yml` complet joué de zéro sans erreur, puis smoke test à travers Apache + ModSecurity. Tests de panne sous charge (`scripts/probe.py`, 5 achats/s) :

  | Panne | Ce qu'a vu le client | Retour |
  |---|---|---|
  | Primaire PostgreSQL tué | 43 s d'erreurs 503, aucune perte (stock cohérent, tous les billets émis) | Patroni a promu le réplica ; l'ancien primaire est revenu seul en réplica |
  | Bascule planifiée (`switchover`) | ~10 s d'interruption, réponses 503 (le client rejoue avec la même clé) | — |
  | Nœud RabbitMQ tué | aucune erreur | file quorum servie par les 2 autres nœuds |
  | Serveur d'app tué | aucune erreur | Apache l'a retiré de la rotation |
  | Redémarrage de toutes les VM | — | cluster et services revenus seuls |

- **Pas encore exécuté sur GCP** : `tofu apply`, LB et health checks Google, NFS noyau et bascule du disque régional, IAP / OS Login, certificat. Le labo remplace l'IP virtuelle PostgreSQL par HAProxy et le NAS par un volume partagé.
