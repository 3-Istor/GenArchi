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
- **GCP, 2026-11-15** (projet de test, sans Cloud Armor faute de quota) : `tofu apply` après trois correctifs ; smoke 10/10, billet émis en 8 s par Eventarc Firestore ; région retirée du LB pendant 10 min, 0 échec sur 4 407 commandes. L'ancien job de panne n'a produit aucune panne (révision jamais prête) et la canary a promu `europe-west4` sans trafic : d'où l'[ADR 0019](../../docs/adr/0019-p3-panne-de-region-et-canary.md) (drapeau Firestore, routage par en-tête, trafic de canary).
- **GCP, 2026-11-16** (mécanisme de l'ADR 0019, sonde à 5 achats/s) : `make p3-chaos-region` pose le drapeau sur `europe-west1` ; le `/readyz` de la région passe à 503 pendant 10 min, le LB sert `europe-west4` environ 20 s après et revient seul sur `europe-west1` à l'expiration. 0 échec sur 4 071 commandes, plus longue interruption 6,6 s, stock cohérent. Routage par en-tête vérifié sur les deux régions. `make p3-canary` avec son propre trafic : 247 requêtes sur la canary d'`europe-west1` et 141 sur celle d'`europe-west4`, 0 erreur 5xx, les deux promues ; `/version` montre la nouvelle image sur ~10 % des réponses pendant la fenêtre ; 0 échec sur 7 302 commandes côté client.
- **Pas encore exécuté sur GCP** : Cloud Armor (quota à 0).
