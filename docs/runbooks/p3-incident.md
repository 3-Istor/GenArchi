# P3 — Alertes et test de panne

La P3 se répare seule ; l'humain observe, explique et corrige la cause.

## Alerte « SLO burn rate »

Le budget d’erreur (0,1 % de requêtes en 5xx sur 28 jours) est consommé 10 fois trop vite.

1. Monitoring → Services → *GenArchi P3 API* : quelle région, depuis quand.
2. Logs : `resource.type="cloud_run_revision" severity>=ERROR`, filtrer par `trace` pour suivre une requête de bout en bout.
3. Une nouvelle révision vient d'arriver ? La canary aurait dû la retirer ; sinon retour arrière ([`p3-deploy.md`](p3-deploy.md)).
4. Une région entière est en erreur ? Le LB doit déjà l'avoir retirée (*service health*). Vérifier `make p3-smoke`.

## Test de panne de région (T4)

Chaque nuit à 03:17 (Europe/Paris), le job `p3-chaos-region` pose le document Firestore `chaos/<première région>` pour 10 minutes : toutes les instances de l'API de cette région répondent 503 sur `/readyz` (relu toutes les 5 s), sans nouvelle révision, et le drapeau expire seul. Pendant la fenêtre : la sonde externe doit rester verte et le SLO ne pas bouger. C'est la preuve permanente que le PRA fonctionne ([ADR 0019](../adr/0019-p3-panne-de-region-et-canary.md)).

Le lancer à la demande (avec l'accord de l'équipe) :

```bash
make p3-chaos-region
```

Observer : `GET https://p3.genarchi.3istor.com/version` répond depuis l'autre région en moins d'une minute.

Observer une région précise : ajouter l'en-tête `X-GenArchi-Region: europe-west4` (ou `europe-west1`), que le LB route vers cette seule région. Avec cet en-tête, tous les chemins vont à l'API : le front n'y est pas servi (404).

Arrêter le test en cours : reposer le drapeau à l'instant présent, `gcloud run jobs execute p3-chaos-region --region europe-west1 --args=chaos-region,--region,europe-west1,--seconds,0`. Les instances redeviennent prêtes environ 10 s après l'écriture (relecture toutes les 5 s, puis la sonde de readiness), et le LB revient ensuite sur la région.

Désactiver : `chaos_enabled = false` (variable OpenTofu).
