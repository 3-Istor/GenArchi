# Contrat d'exécution de l'application

Contrat `0.1.0`. Ce document est l'interface entre **le code de l'app** et **les plateformes**.
Si l'app respecte la partie A et que chaque plateforme fournit la partie B, la même version du code tourne en local, en P2 et en P3 sans modification.

---

## A. Ce que l'application DOIT faire

### A1. Processus

L'app est un seul paquet qui expose quatre commandes :

| Commande | Rôle | Local | P2 | P3 |
|---|---|---|---|---|
| `serve-api` | Serveur HTTP de l'API (`contracts/api/openapi.yaml`) | ✅ | `app-01`, `app-02` (systemd) | Cloud Run service `api` |
| `serve-worker` | Serveur HTTP qui reçoit les push Pub/Sub sur `POST /internal/tickets/issue` | ✅ | ❌ (pas de bus) | Cloud Run service `worker` |
| `issue-pending [--limit N]` | Émet les QR des billets `pending` puis se termine | ✅ | `batch-01`, toutes les 15 min (timer systemd) | Sweeper : Cloud Run job planifié, toutes les 5 min, ne traite que les `pending` de plus de 2 min |
| `migrate` | Crée ou migre le schéma (tables SQL ou index Firestore) | ✅ | Lancé à la main via runbook | Cloud Run job, lancé par la CI avant le déploiement |

Les deux déclencheurs d'émission (`serve-worker` et `issue-pending`) appellent **la même fonction** `issue_ticket(ticket_id)`, idempotente (invariant I5).

### A2. Packaging

- **Sans container** (P2) : installable par `pip install <wheel>` dans un virtualenv, les commandes ci-dessus étant des points d'entrée console. Aucune dépendance système au-delà de Python 3.11+ et `libpq` (P2).
- **Container** (local, P3) : un `Dockerfile` à la racine de `app/` produit une image OCI qui lance `serve-api` par défaut ; la commande est surchargée pour les autres processus.
- Une seule version de code = un seul tag git = une wheel + une image construites par la CI.

### A3. Configuration (12 facteurs)

- **Toute** la configuration passe par des variables d'environnement (liste en partie C). Aucune valeur d'environnement en dur, aucun fichier de config à éditer sur un serveur.
- Les secrets (`ADMIN_TOKEN`, `STAFF_TOKEN`, mot de passe de base) arrivent aussi par variables d'environnement ; c'est la plateforme qui les injecte depuis son coffre.
- Variable inconnue ou obligatoire manquante → l'app **refuse de démarrer** avec un message explicite.

### A4. Ports et adaptateurs

Le code métier ne dépend que de ces interfaces. Un adaptateur par backend, choisi au démarrage par variable d'environnement.

```text
EventRepository       get(event_id) / list(status, limit, cursor) / create(event)
OrderService          place_order(event_id, idempotency_key, buyer_email, quantity) -> Order
                      # atomique : I1 + I2 dans une transaction
TicketRepository      get(ticket_id) / list_pending(older_than, limit) / mark_issued(ticket_id, qr_object, at)
                      / mark_scanned(ticket_id, at) -> (Ticket, already_scanned: bool)
BlobStore             put(key, bytes, content_type) / get(key) -> bytes / signed_url(key, ttl) -> url | None
EventPublisher        publish(cloud_event)            # no-op en P2
```

| Interface | `local` | `p2` | `p3` |
|---|---|---|---|
| Repositories + OrderService | `postgres` (compose) ou `firestore` (émulateur) | `postgres` | `firestore` |
| BlobStore | `fs` (dossier local) | `fs` (partage NFS monté sur `/mnt/tickets`) | `gcs` |
| EventPublisher | `none` ou `pubsub` (émulateur) | `none` | `pubsub` |

Les tests de contrat (`contracts/tests/acceptance.md`) sont lancés **sur chaque combinaison d'adaptateurs** : c'est ce qui prouve que P2 et P3 servent bien la même app.

### A5. Comportement

| Exigence | Détail |
|---|---|
| Port | Écoute sur `0.0.0.0:$PORT` (défaut `8080`) |
| Sans état | Aucune session, aucun cache métier, aucun fichier écrit hors de `/tmp` (I6) |
| Démarrage | Prêt en moins de **5 s** hors migrations ; `/healthz` répond dès que le serveur écoute, `/readyz` seulement quand la base répond |
| Arrêt | Sur `SIGTERM` : arrête d'accepter, termine les requêtes en cours, sort en moins de **10 s** |
| Logs | Une ligne JSON par événement sur **stdout** (champs ci-dessous). Jamais de fichier de log géré par l'app |
| Traces | Propage l'en-tête W3C `traceparent` (HTTP entrant → CloudEvent sortant → worker). Exporte en OTLP si `OTEL_EXPORTER_OTLP_ENDPOINT` est défini ; sinon ne fait rien |
| Timeouts | Appels base ≤ 2 s, appels blob ≤ 5 s, publication ≤ 2 s. Publication échouée = log `warning`, la requête d'achat **réussit quand même** (le sweeper rattrape) |
| Identité | `GET /version` renvoie plateforme, région/zone, instance, version de code et version de contrat |

Champs de log obligatoires :

```json
{"ts":"2026-12-04T17:00:01.234Z","severity":"INFO","message":"order placed",
 "platform":"p3","process":"api","instance":"api-00042-xyz",
 "request_id":"…","trace_id":"…","span_id":"…",
 "event_id":"evt_…","order_id":"ord_…","http_status":201,"latency_ms":37}
```

`severity` ∈ `DEBUG, INFO, WARNING, ERROR, CRITICAL` (noms compris nativement par Cloud Logging). En P3, `trace_id` est aussi écrit dans le champ `logging.googleapis.com/trace` pour corréler logs et traces.

---

## B. Ce que chaque plateforme DOIT fournir

| Fourniture | P2 | P3 |
|---|---|---|
| Point d'entrée HTTP(S) public | Load balancer régional → nginx (`web-0x`) → `app-0x:8080` | Load balancer global → Cloud Run `api` (2 régions) |
| Health check | Sur `/readyz`, intervalle 5 s, 2 échecs = retiré | Probes Cloud Run sur `/readyz` + outlier detection du LB |
| Variables d'env | Fichier `/etc/genarchi/genarchi.env` (mode 0600) écrit par Ansible, chargé par systemd | Variables de service Cloud Run, secrets montés depuis Secret Manager |
| Base de données | PostgreSQL 15, DSN via `DATABASE_URL` vers `db-primary.p2.genarchi.internal` | Firestore base `(default)` en `eur3` |
| Stockage blob | Partage NFS monté sur `/mnt/tickets` sur `app-0x` et `batch-01` | Bucket Cloud Storage `BLOB_GCS_BUCKET` |
| Bus d'événements | Aucun | Topics `ticket-purchased`, `ticket-issued`, `ticket-purchased-dlq` + abonnements push vers `worker` |
| Déclenchement de `issue-pending` | Timer systemd sur `batch-01` (`*:0/15`) | Cloud Scheduler → Cloud Run job, toutes les 5 min |
| Collecte des logs | journald → agent Zabbix (erreurs) ; consultation par SSH | Automatique (stdout → Cloud Logging) |
| Traces | Aucune (hors périmètre P2) | Cloud Trace via OTLP |
| Identité machine | `INSTANCE_NAME`, `ZONE` posés par Ansible | `K_SERVICE`, `K_REVISION` fournis par Cloud Run ; `REGION` posé par Terraform |

---

## C. Variables d'environnement

| Variable | Obligatoire | Valeurs / exemple | Utilisée par |
|---|---|---|---|
| `PLATFORM` | oui | `local`, `p2`, `p3` | tous |
| `PORT` | non | `8080` | serveurs |
| `LOG_LEVEL` | non | `INFO` | tous |
| `PUBLIC_BASE_URL` | oui | `https://p3.genarchi.example` | api, émission (contenu du QR) |
| `DATA_BACKEND` | oui | `postgres`, `firestore` | tous |
| `DATABASE_URL` | si `postgres` | `postgresql://genarchi:***@db-primary.p2.genarchi.internal:5432/genarchi` | tous |
| `FIRESTORE_PROJECT` | si `firestore` | `genarchi-p3` | tous |
| `FIRESTORE_DATABASE` | non | `(default)` | tous |
| `BLOB_BACKEND` | oui | `fs`, `gcs` | api, émission |
| `BLOB_FS_ROOT` | si `fs` | `/mnt/tickets` | api, émission |
| `BLOB_GCS_BUCKET` | si `gcs` | `genarchi-p3-tickets` | api, émission |
| `EVENTS_BACKEND` | oui | `none`, `pubsub` | api, worker |
| `PUBSUB_PROJECT` | si `pubsub` | `genarchi-p3` | api, worker |
| `PUBSUB_TOPIC_TICKET_PURCHASED` | si `pubsub` | `ticket-purchased` | api, sweeper |
| `PUBSUB_TOPIC_TICKET_ISSUED` | si `pubsub` | `ticket-issued` | worker |
| `ADMIN_TOKEN` | oui | secret | api |
| `STAFF_TOKEN` | oui | secret | api |
| `CHAOS_ENABLED` | non | `false` (défaut), `true` en campagne de test | api, worker |
| `CHAOS_FORCE_UNREADY` | non | `false` (défaut). `true` : `/readyz` renvoie toujours 503 (simulation de perte de région, test T4) | api |
| `INSTANCE_NAME` | P2 | `app-01` | `/version`, logs |
| `ZONE` | P2 | `europe-west9-a` | `/version` |
| `REGION` | P3 | `europe-west1` | `/version` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | non | vide = pas d'export | tous |
| `OTEL_SERVICE_NAME` | non | `genarchi-api` | tous |
| `FIRESTORE_EMULATOR_HOST` | local | `firestore:8080` | local |
| `PUBSUB_EMULATOR_HOST` | local | `pubsub:8085` | local |

Exemples complets : [`env.local.example`](env.local.example), [`env.p2.example`](env.p2.example), [`env.p3.example`](env.p3.example).
