# P3 — Déployer, canary, retour arrière

## Prérequis (une fois par poste)

1. Outils : `nix develop` ou `mise install` ; `make doctor` vert. Docker n'est **pas** nécessaire (Cloud Build construit l'image).
2. `gcloud auth login` puis `gcloud auth application-default login`.
3. `cp infra/p3/env.mk.example infra/p3/env.mk`, remplir `P3_PROJECT` et `TF_STATE_BUCKET`.
4. `export CLOUDFLARE_API_TOKEN=…` (jeton « DNS edit » sur `3istor.com`).

## Premier déploiement

```bash
make bootstrap     # une seule fois pour l'équipe (bucket d'état)
make p3-deploy     # registre → image (Cloud Build) → infra complète → smoke
```

Le certificat géré par Google est émis 15 à 60 min après que `p3.genarchi.3istor.com` pointe sur le LB ; pendant ce temps `p3-smoke` échoue en TLS.

Créer les index Firestore et la base prend quelques minutes au premier `apply`.

## Mettre une version en production

```bash
git checkout <tag>
make p3-canary
```

Pour chaque région, l'une après l'autre : nouvelle révision sans trafic → 10 % du trafic pendant 5 min → si plus de 2 % de 5xx (contrat P3), **retour automatique** à la révision stable et arrêt ; sinon 100 %. Puis OpenTofu enregistre l'image (le worker et les jobs passent aussi à la nouvelle version).

Réglages : `WATCH_SECONDS=600 MAX_ERROR_RATIO=0.01 make p3-canary`.

## Retour arrière manuel

Rarement nécessaire (la canary le fait). Sinon : `gcloud run services update-traffic p3-api --region <r> --to-revisions <révision>=100` dans chaque région, puis redéployer l'ancien tag avec `make p3-canary`.
