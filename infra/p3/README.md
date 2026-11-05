# Infrastructure Platform 3 — born to be cloud

Aucun serveur : services Cloud Run sans état dans deux régions, données multi-région, événements émis par la base, mises en production progressives et test de panne permanent. Spec : [`docs/architecture/platform3.md`](../../docs/architecture/platform3.md).

```text
Internet ─TLS─▶ LB HTTP(S) global + Cloud Armor (WAF OWASP, 600 req/min/IP)
                 ├─ /  ─▶ bucket du front (Cloud CDN)
                 └─ API ─▶ Cloud Run p3-api  europe-west1 │ europe-west4   (min 1 instance, readiness /readyz)
Firestore (eur3, PITR, sauvegarde quotidienne) ── billet créé ─▶ Eventarc ─▶ Cloud Run p3-worker (2 régions)
p3-worker ─▶ QR dans GCS dual-région (turbo) ; ─▶ Pub/Sub ticket-issued ─▶ BigQuery
Cloud Scheduler : p3-issue-pending (5 min, 2 régions) ; p3-chaos-region (nuit, 10 min de région « non prête »)
Monitoring : sonde externe, SLO 99,9 %, alerte burn rate
```

| Fichier | Contenu |
|---|---|
| `main.tf` | Providers, API, Artifact Registry |
| `iam.tf` | Un compte de service par composant, droits minimaux |
| `data.tf` | Firestore + index + sauvegardes, buckets, Pub/Sub → BigQuery, secrets |
| `run.tf` | Services API et worker, triggers Eventarc, jobs planifiés (rattrapage, chaos) |
| `edge.tf` | LB global, NEG serverless, Cloud Armor, CDN, certificat géré, redirection HTTP, DNS Cloudflare |
| `monitoring.tf` | Sonde, SLO, alertes |
| `scripts/` | Build de l'image (Cloud Build), smoke, canary avec retour arrière automatique |

Cibles : `make p3-plan`, `p3-deploy`, `p3-canary`, `p3-smoke`, `p3-chaos-region`, `p3-destroy`. Variables : [`env.mk.example`](env.mk.example), [`variables.tf`](variables.tf).

## Ce qui a été vérifié

- `tofu validate` (providers google 8.x, cloudflare 5.x) ; attributs contrôlés contre le schéma des providers ; frontière P2/P3 respectée.
- L'app tourne en local « comme en P3 » (émulateurs Firestore et Pub/Sub, `make up-p3 smoke-local`) et passe les tests de contrat sur Firestore, dont 200 achats concurrents sur 100 places.
- **Pas encore exécuté sur GCP** : `tofu apply`, Eventarc Firestore, bascule *service health*, canary, chaos nocturne.
