# Règles pour travailler dans `infra/p2/`

Ce dossier est la **Platform 2** : un datacenter d'entreprise virtualisé dans GCP. Le but pédagogique est de montrer l'ancienne génération **telle qu'elle était**. Ne pas la moderniser.

Avant toute modification, lire :
- `contracts/platforms/platform2.md` (ce que la P2 promet, interface Terraform)
- `docs/architecture/platform2.md` (spec : inventaire, réseau, flux)
- `docs/architecture/challenge.md` § 2 (lignes rouges P2)

## Interdit ici (vérifié par `scripts/check_boundary.py`)

Containers, Cloud Run, GKE, Cloud SQL et tout DBaaS, Firestore, Pub/Sub, buckets pour les données de l'app, Managed Instance Groups, autoscalers, load balancer global.

## Interdit aussi (non vérifiable automatiquement, à respecter)

- Bascule de base automatique (Patroni, repmgr, pg_auto_failover)
- Alerte qui déclenche une action automatique
- Pipeline CI qui déploie l'app sur les VM
- VM Manager / OS patch management automatique
- Règles firewall par tag ou service account : en P2 on écrit les règles **par plage d'IP de sous-réseau**

## Attendu

- VM nommées (`web-01`, `app-01`, `db-01`…), IP internes fixes (voir spec)
- Terraform construit, Ansible installe, **les humains exploitent** via `ops/runbooks/p2-*.md`
- Tout changement de run passe par une issue « Demande de changement » approuvée
- Labels `platform = "p2"` partout
- Ne jamais lancer `terraform apply` ni `destroy` sans validation humaine explicite
