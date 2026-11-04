# Contrat d'exécution de l'application

Contrat `0.2.0`. Ce document est l'interface entre **le code de l'app** (`app/`) et **les plateformes** (`infra/p2`, `infra/p3`).
Si l'app respecte la partie A et que chaque plateforme fournit la partie B, la même version du code tourne en local, en P2 et en P3 sans modification.

Changements depuis `0.1.0` : architectures « état de l'art » validées le 2026-11-04 (voir [`docs/architecture/`](../../docs/architecture/README.md)).
- P2 : les QR sont émis par des workers qui consomment une file **RabbitMQ** (plus de batch toutes les 15 min) ; un rattrapage périodique reste lancé par l'ordonnanceur.
- P3 : l'API **ne publie plus** d'événement. C'est **Firestore** qui émet l'événement « document billet créé », livré au worker par **Eventarc**. Le worker publie `ticket.issued` sur Pub/Sub, qui alimente BigQuery.

---

## A. Ce que l'application DOIT faire

### A1. Processus

Un seul paquet Python (`genarchi`), une seule commande `genarchi <sous-commande>` :

| Sous-commande | Rôle | Local | P2 | P3 |
|---|---|---|---|---|
| `serve-api` | API HTTP ([`openapi.yaml`](../api/openapi.yaml)) | ✅ | 4 VM `app-*` (systemd) | Cloud Run `api`, 2 régions |
| `serve-worker` | Reçoit les CloudEvents Firestore sur `POST /internal/events/ticket-created` | ✅ (profil p3) | ❌ | Cloud Run `worker`, 2 régions |
| `consume` | Consomme la file RabbitMQ `tickets.issue` | ✅ (profil p2) | 4 VM `app-*` (systemd, à côté de l'API) | ❌ |
| `issue-pending [--older-than S] [--limit N]` | Rattrapage : émet les billets `pending` trop anciens, puis s'arrête | ✅ | Ordonnanceur, toutes les 5 min | Cloud Run job planifié, toutes les 5 min |
| `migrate` | Crée ou met à jour le schéma (SQL) ; no-op en Firestore | ✅ | Runbook de mise en production | — |
| `seed [--capacity N]` | Crée un événement de démonstration | ✅ | Runbook | Cloud Run job à la demande |

Les trois déclencheurs d'émission (`serve-worker`, `consume`, `issue-pending`) appellent **la même fonction** `issue_ticket(ticket_id)`, idempotente (invariant I5).

### A2. Packaging

- **Sans conteneur** (P2) : `uv build` produit une wheel installée dans un virtualenv sur la VM ; `genarchi` est un point d'entrée console. Python ≥ 3.11, aucune bibliothèque système requise (pilotes en pur Python ou wheels binaires).
- **Conteneur** (local, P3) : [`app/Dockerfile`](../../app/Dockerfile) produit une image OCI non-root qui lance `genarchi serve-api` ; la commande est surchargée pour les autres processus.
- Une version de code = un tag git = une wheel + une image.

### A3. Configuration (12 facteurs)

- **Toute** la configuration passe par des variables d'environnement (partie C). Aucune valeur d'environnement en dur.
- Les secrets (`ADMIN_TOKEN`, `STAFF_TOKEN`, mots de passe) arrivent aussi par l'environnement ; c'est la plateforme qui les injecte depuis son coffre.
- Variable obligatoire manquante ou valeur invalide → l'app **refuse de démarrer** avec un message explicite.

### A4. Ports et adaptateurs

Le code métier (`genarchi.domain`) ne dépend que de ces interfaces ; l'adaptateur est choisi au démarrage.

```text
Store            get_event / list_events / create_event
                 place_order(event_id, idempotency_key, buyer_email, quantity) -> (Order, created: bool)   # I1 + I2 atomiques
                 get_order / get_ticket / list_pending(older_than, limit)
                 mark_issued(ticket_id, qr_object, at) / mark_scanned(ticket_id, at) -> (Ticket, already: bool)
                 stats(event_id) / ping()
BlobStore        put(key, data, content_type) / get(key) / signed_url(key, ttl) -> url | None
Publisher        publish(cloud_event)
```

| Interface | Profil local « p2 » | Profil local « p3 » | P2 | P3 |
|---|---|---|---|---|
| `Store` | `postgres` | `firestore` (émulateur) | `postgres` (via l'IP virtuelle du cluster) | `firestore` |
| `BlobStore` | `fs` | `fs` | `fs` (NFS monté sur `/mnt/tickets`) | `gcs` |
| `Publisher` côté API | `rabbitmq` | `none` | `rabbitmq` | `none` (Firestore émet) |
| `Publisher` côté worker | `none` | `none` ou `pubsub` (émulateur) | `none` | `pubsub` (`ticket.issued`) |

Les tests de contrat sont lancés sur chaque profil : c'est ce qui prouve que P2 et P3 servent bien la même app.

### A5. Comportement

| Exigence | Détail |
|---|---|
| Port | Écoute sur `0.0.0.0:$PORT` (défaut `8080`) |
| Sans état | Aucune session, aucun cache métier, aucun fichier écrit hors de `/tmp` et du stockage blob (I6) |
| Démarrage | Prêt en moins de 5 s ; `/healthz` répond dès que le serveur écoute, `/readyz` seulement si la base répond |
| Arrêt | Sur `SIGTERM` : termine les requêtes en cours et sort en moins de 10 s |
| Logs | Une ligne JSON par événement sur stdout (`ts`, `severity`, `message`, `platform`, `process`, `instance`, `request_id`, `trace_id` + champs métier) |
| Traces | Propage `traceparent` (HTTP → message → worker). Export OTLP seulement si `OTEL_EXPORTER_OTLP_ENDPOINT` est défini |
| Publication | Après commit. Échec de publication = log `WARNING`, l'achat **réussit quand même** : `issue-pending` rattrape |
| Identité | `GET /version` : plateforme, région ou zone, instance, version de code, version de contrat |

`severity` ∈ `DEBUG, INFO, WARNING, ERROR, CRITICAL`. En P3, la trace est aussi écrite dans `logging.googleapis.com/trace`.

---

## B. Ce que chaque plateforme DOIT fournir

| Fourniture | P2 | P3 |
|---|---|---|
| Entrée publique | LB régional (TLS) → Apache + ModSecurity (`rp-*`) → `app-*:8080` | LB global (TLS, Cloud Armor) → Cloud Run `api` (2 régions) |
| Health check | `/readyz`, 5 s, 2 échecs = retiré | Probe de readiness Cloud Run sur `/readyz` (service health) |
| Variables d'env | `/etc/genarchi/genarchi.env` (0600) écrit par Ansible | Variables Cloud Run, secrets depuis Secret Manager |
| Base | PostgreSQL 17 + Patroni, joint via `db.p2.genarchi.internal` (IP virtuelle) | Firestore `(default)` en `eur3` |
| Blob | NFS monté sur `/mnt/tickets` (NAS actif, disque répliqué) | Bucket `BLOB_GCS_BUCKET` (dual-région) |
| Événements | RabbitMQ 3 nœuds : exchange `genarchi.events`, file quorum `tickets.issue` | Trigger Eventarc `google.cloud.firestore.document.v1.created` sur `tickets/{id}` → `worker` ; topic `ticket-issued` → BigQuery |
| `issue-pending` | Timer systemd sur `scheduler`, toutes les 5 min | Cloud Scheduler → Cloud Run job, toutes les 5 min |
| Logs | journald + rsyslog central sur `monitoring` | stdout → Cloud Logging |
| Identité machine | `INSTANCE_NAME`, `ZONE` posés par Ansible | `K_SERVICE`, `K_REVISION` (Cloud Run), `REGION` posé par OpenTofu |

---

## C. Variables d'environnement

| Variable | Obligatoire | Valeurs / exemple |
|---|---|---|
| `PLATFORM` | oui | `local`, `p2`, `p3` |
| `PORT` | non | `8080` |
| `LOG_LEVEL` | non | `INFO` |
| `PUBLIC_BASE_URL` | oui | `https://p3.genarchi.3istor.com` |
| `DATA_BACKEND` | oui | `postgres`, `firestore`, `memory` (tests) |
| `DATABASE_URL` | si `postgres` | `postgresql://genarchi:***@db.p2.genarchi.internal:5432/genarchi` |
| `FIRESTORE_PROJECT` | si `firestore` | `genarchi-p3` |
| `FIRESTORE_DATABASE` | non | `(default)` |
| `BLOB_BACKEND` | oui | `fs`, `gcs`, `memory` (tests) |
| `BLOB_FS_ROOT` | si `fs` | `/mnt/tickets` |
| `BLOB_GCS_BUCKET` | si `gcs` | `genarchi-p3-tickets` |
| `EVENTS_BACKEND` | oui | `none`, `rabbitmq`, `pubsub` |
| `AMQP_URLS` | si `rabbitmq` | `amqp://genarchi:***@mq-1:5672/,amqp://genarchi:***@mq-2:5672/` (essayés dans l'ordre) |
| `PUBSUB_PROJECT` | si `pubsub` | `genarchi-p3` |
| `PUBSUB_TOPIC_TICKET_ISSUED` | si `pubsub` | `ticket-issued` |
| `ADMIN_TOKEN` | oui | secret |
| `STAFF_TOKEN` | oui | secret |
| `CHAOS_ENABLED` | non | `false` (défaut) |
| `CHAOS_FORCE_UNREADY` | non | `false` (défaut) ; `true` : `/readyz` renvoie toujours 503 (perte de région simulée, T4) |
| `INSTANCE_NAME` | non | `app-1a` (P2) ; sinon `K_REVISION` ou le nom d'hôte |
| `ZONE` / `REGION` | non | `europe-west9-a` (P2) / `europe-west1` (P3) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | non | vide = pas d'export |
| `FIRESTORE_EMULATOR_HOST`, `PUBSUB_EMULATOR_HOST` | local | `localhost:8681`, `localhost:8682` |

Exemples : [`env.local.example`](env.local.example), [`env.p2.example`](env.p2.example), [`env.p3.example`](env.p3.example).
