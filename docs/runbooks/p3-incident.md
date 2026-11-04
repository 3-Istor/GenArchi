# P3 — Alertes et test de panne

La P3 se répare seule ; l'humain observe, explique et corrige la cause.

## Alerte « SLO burn rate »

Le budget d'erreur (0,5 % de requêtes en 5xx sur 28 jours) est consommé 10 fois trop vite.

1. Monitoring → Services → *GenArchi P3 API* : quelle région, depuis quand.
2. Logs : `resource.type="cloud_run_revision" severity>=ERROR`, filtrer par `trace` pour suivre une requête de bout en bout.
3. Une nouvelle révision vient d'arriver ? La canary aurait dû la retirer ; sinon retour arrière ([`p3-deploy.md`](p3-deploy.md)).
4. Une région entière est en erreur ? Le LB doit déjà l'avoir retirée (*service health*). Vérifier `make p3-smoke`.

## Test de panne de région (T4)

Chaque nuit à 03:17 (Europe/Paris), le job `p3-chaos-region` rend l'API de la première région « non prête » pendant 10 minutes, puis la rétablit. Pendant la fenêtre : la sonde externe doit rester verte et le SLO ne pas bouger. C'est la preuve permanente que le PRA fonctionne.

Le lancer à la demande (avec l'accord de l'équipe) :

```bash
make p3-chaos-region
```

Observer : `GET https://p3.genarchi.3istor.com/version` répond depuis l'autre région en moins d'une minute.

Arrêter le test en cours : `gcloud run jobs executions cancel <exécution> --region europe-west1`, puis `gcloud run services update p3-api --region europe-west1 --update-env-vars CHAOS_FORCE_UNREADY=false`.

Désactiver : `chaos_enabled = false` (variable OpenTofu).
