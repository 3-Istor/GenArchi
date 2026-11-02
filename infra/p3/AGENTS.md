# Règles pour travailler dans `infra/p3/`

Ce dossier est la **Platform 3** : application née dans le cloud, serverless, multi-région, pilotée par les événements, exploitée en SRE / NoOps.

Avant toute modification, lire :
- `contracts/platforms/platform3.md` (ce que la P3 promet, interface Terraform)
- `docs/architecture/platform3.md` (spec : inventaire, identités, flux)
- `docs/architecture/challenge.md` § 3 à 5 (lignes rouges P3, choix serverless)

## Interdit ici (vérifié par `scripts/check_boundary.py`)

VM, templates d'instance, groupes d'instances, disques persistants, Filestore, clés de service account exportées.

## Interdit aussi

- Une seule région, ou une donnée stockée dans une seule zone
- Toute action manuelle de déploiement ou de correction (console, `gcloud` à la main)
- État local dans les instances
- Traitement métier en batch planifié (le sweeper est un filet de réconciliation, voir ADR 0011)

## Attendu

- `api` et `worker` dans **au moins 2 régions**, `min_instances ≥ 1` pour `api` (requis par Cloud Run service health)
- Un compte de service par composant, droits minimaux (tableau dans la spec)
- SLO, alertes, sauvegardes, chaos nocturne et canary décrits **en Terraform** ou dans la CI
- Labels `platform = "p3"` partout
- Ne jamais lancer `terraform apply` ni `destroy` sans validation humaine explicite
