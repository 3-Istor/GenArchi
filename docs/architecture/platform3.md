# Spec d'architecture — Platform 3 « Born to be Cloud »

> **Statut : à challenger** (voir [`challenge.md`](challenge.md)). Spec texte d'abord, schémas Noodle ensuite.
> Contrat associé : [`contracts/platforms/platform3.md`](../../contracts/platforms/platform3.md).
> Les IDs (`p3-…`) sont stables : ce sont ceux du futur `architecture/p3/model.yaml` Noodle.

## 1. Principe

Aucun serveur à soi. L'app est découpée en **processus sans état et jetables** (Cloud Run), actifs dans **deux régions** en même temps, branchés sur des **services managés multi-région** (Firestore, Cloud Storage, Pub/Sub). Les traitements sont déclenchés par des **événements**. Tout, exploitation comprise, est décrit en code ; les pannes se réparent sans humain ; la reprise d'activité est **testée en permanence**.

Choix de compute : **serverless (Cloud Run)** plutôt que Kubernetes managé. Justification et limites : [`challenge.md` § 4](challenge.md#4-serverless-plutôt-que-kubernetes-managé).

## 2. Zones (régions et groupes Noodle)

| ID | Kind | Titre | Sous-titre | Contient |
|---|---|---|---|---|
| `p3-internet` | region | INTERNET | — | `p3-user`, `p3-dev` |
| `p3-google-edge` | region | GOOGLE GLOBAL EDGE | anycast | `p3-glb`, `p3-armor`, `p3-cdn` |
| `p3-gcp` | region | GCP PROJECT GENARCHI-P3 | — | tout le reste |
| `p3-ew1` | region | REGION EUROPE-WEST1 | Belgique | `p3-api-ew1`, `p3-worker-ew1`, `p3-sweeper-ew1` |
| `p3-ew4` | region | REGION EUROPE-WEST4 | Pays-Bas | `p3-api-ew4`, `p3-worker-ew4`, `p3-sweeper-ew4` |
| `p3-data` | group | MANAGED DATA | multi-région EU | `p3-firestore`, `p3-tickets-bucket`, `p3-front-bucket` |
| `p3-messaging` | group | EVENTS | Pub/Sub (global) | topics et abonnements |
| `p3-identity` | group | IDENTITY & SECRETS | — | `p3-secrets`, comptes de service |
| `p3-observability` | group | OBSERVABILITY | — | `p3-logging`, `p3-monitoring`, `p3-trace` |
| `p3-delivery` | group | DELIVERY | — | `p3-github-actions`, `p3-registry`, `p3-terraform` |

## 3. Réseau

Pas de VPC à gérer pour l'app : le réseau est **défini par l'application** (SDN du cours).

| Mécanisme | Réglage |
|---|---|
| Entrée publique | Uniquement le load balancer global (IP anycast) |
| `p3-api-*` | `ingress = internal-and-cloud-load-balancing` : l'URL `*.run.app` est fermée à Internet |
| `p3-worker-*` | `ingress = internal`, `run.invoker` réservé au compte de service des abonnements push |
| Contrôle des flux | Par **identité** (IAM, un compte de service par composant), pas par adresse IP |
| WAF | Cloud Armor sur le backend API : règles OWASP préconfigurées (SQLi, XSS), limitation de débit par IP |
| Buckets | `public access prevention` activé ; QR servis par URL signée (15 min) |
| `/internal/*` | Seul `/internal/chaos` est routé par le LB (jeton admin + `CHAOS_ENABLED`) |

Flux explicitement interdits à dessiner (`denied: true`) : `p3-user` → `p3-api-ew1` en direct (`enforced_by`: réglage ingress), `p3-user` → `p3-worker-*` (ingress + IAM), `p3-user` → `p3-tickets-bucket` sans URL signée (public access prevention).

## 4. Inventaire des composants

| ID | Titre | Tech | Kind | Zone | Ports (écoute) | Réglages clés | Rôle |
|---|---|---|---|---|---|---|---|
| `p3-user` | Acheteur | navigateur | external (actor) | internet | — | — | Achète et télécharge |
| `p3-dev` | Équipe | git push | external (actor) | internet | — | — | Seule action humaine : un merge |
| `p3-glb` | Load balancer global | Global external Application LB | cloud | edge | `https` TCP 443 (`http` 80 sans domaine) | URL map : `/` → front, `/api` et le reste → backend API ; outlier detection | Point d'entrée unique, route vers la région saine la plus proche |
| `p3-armor` | WAF | Cloud Armor | security | edge | — | OWASP + rate limit | Filtrage L7 |
| `p3-cdn` | Cache | Cloud CDN | cloud | edge | — | Sur le backend bucket front | Sert le front statique |
| `p3-api-ew1` | api | Cloud Run service | backend | ew1 | `https` TCP 443 | **min 1** (exigé par service health), max 20, concurrence 80, CPU boost au démarrage, probe readiness HTTP/1 `/readyz` | API |
| `p3-api-ew4` | api | Cloud Run service | backend | ew4 | `https` TCP 443 | idem | API |
| `p3-worker-ew1` | worker | Cloud Run service | backend | ew1 | `https` TCP 443 | ingress internal, min 0, max 10 | Émission des QR sur événement |
| `p3-worker-ew4` | worker | Cloud Run service | backend | ew4 | `https` TCP 443 | idem | idem |
| `p3-sweeper-ew1` | sweeper | Cloud Run job + Cloud Scheduler | backend | ew1 | — | toutes les 5 min, `pending` > 2 min | Filet de sécurité (publication perdue) |
| `p3-sweeper-ew4` | sweeper | idem | backend | ew4 | — | idem, idempotent | idem |
| `p3-firestore` | Firestore `(default)` | Firestore natif · eur3 | database (cylinder) | data | `grpc` TCP 443 | PITR 7 j, sauvegarde quotidienne 7 j, suppression protégée | Source de vérité métier |
| `p3-tickets-bucket` | genarchi-p3-tickets | Cloud Storage · EU | database (cylinder) | data | `https` TCP 443 | versioning, soft delete, accès uniforme | QR codes |
| `p3-front-bucket` | genarchi-p3-front | Cloud Storage · EU | database (cylinder) | data | `https` TCP 443 | backend bucket du LB | Front statique |
| `p3-topic-purchased` | ticket-purchased | Pub/Sub topic | bus (pipe) | messaging | `grpc` TCP 443 | rétention 7 j | Événement d'achat |
| `p3-sub-ew1` / `p3-sub-ew4` | issue-ew1 / issue-ew4 | Pub/Sub push subscription | bus (pipe) | messaging | — | push OIDC vers `worker` de sa région, 5 tentatives puis DLQ, backoff exponentiel | Une livraison par région (doublon voulu, traité par l'idempotence I5) |
| `p3-topic-dlq` | ticket-purchased-dlq | Pub/Sub topic | bus (pipe) | messaging | — | alerte si > 0 message | Messages en échec |
| `p3-topic-issued` | ticket-issued | Pub/Sub topic | bus (pipe) | messaging | — | — | Billet émis |
| `p3-bq-sales` | Ventes temps réel | BigQuery + abonnement BigQuery | database | data | — | `status: planned` (bonus) | Stats en direct |
| `p3-secrets` | Secret Manager | Secret Manager | security | identity | — | `admin-token`, `staff-token` | Secrets montés en variables |
| `p3-logging` | Cloud Logging | — | tool | observability | — | logs JSON de stdout | Logs |
| `p3-monitoring` | Cloud Monitoring | SLO + alertes | tool | observability | — | SLO dispo 99,9 % / latence ; alertes burn rate | SLO, uptime checks |
| `p3-trace` | Cloud Trace | via OpenTelemetry | tool | observability | — | — | Traces distribuées |
| `p3-github-actions` | CI/CD | GitHub Actions + WIF | tool | delivery | — | aucune clé | Build, scan, canary, chaos |
| `p3-registry` | Artifact Registry | Docker · europe | tool | delivery | — | scan de vulnérabilités | Images |
| `p3-terraform` | Terraform | `infra/p3` | tool | delivery | — | — | Décrit toute la plateforme |
| `p3-chaos` | DR permanent | Cloud Scheduler → workflow CI `chaos-region` | tool | delivery | — | chaque nuit, une région rendue indisponible 10 min | Test de DRP permanent (exigé par la colonne P3 du cours) |

### Identités (moindre privilège)

| Compte de service | Utilisé par | Droits |
|---|---|---|
| `sa-api` | `p3-api-*`, sweepers | `datastore.user`, `pubsub.publisher` sur `ticket-purchased`, `storage.objectViewer` sur tickets, `serviceAccountTokenCreator` sur lui-même (URL signées), `secretAccessor` sur les deux secrets |
| `sa-worker` | `p3-worker-*` | `datastore.user`, `storage.objectCreator` + `objectViewer` sur tickets, `pubsub.publisher` sur `ticket-issued` |
| `sa-push` | abonnements push | `run.invoker` sur `p3-worker-*` uniquement |
| `sa-ci` | GitHub Actions via WIF | `run.developer`, `artifactregistry.writer`, `iam.serviceAccountUser` sur `sa-api` / `sa-worker` |

## 5. Connexions

| ID | De | Vers | Port | Verbe · protocole | Kind |
|---|---|---|---|---|---|
| `c-user-glb` | `p3-user` | `p3-glb` | https | buy · HTTPS | flow |
| `c-glb-api-ew1` / `c-glb-api-ew4` | `p3-glb` | `p3-api-ew*` (serverless NEG) | https | route · HTTPS | flow |
| `c-glb-front` | `p3-glb` | `p3-front-bucket` | https | serve · HTTPS | flow |
| `c-api-firestore` | `p3-api-*` | `p3-firestore` | grpc | transaction · gRPC | flow |
| `c-api-topic` | `p3-api-*` | `p3-topic-purchased` | grpc | publish · gRPC | flow |
| `c-sub-worker` | Pub/Sub (`p3-sub-ew*`) | `p3-worker-ew*` | https | push · HTTPS + OIDC | flow |
| `c-worker-firestore` | `p3-worker-*` | `p3-firestore` | grpc | mark issued · gRPC | flow |
| `c-worker-bucket` | `p3-worker-*` | `p3-tickets-bucket` | https | put QR · HTTPS | flow |
| `c-worker-issued` | `p3-worker-*` | `p3-topic-issued` | grpc | publish · gRPC | flow |
| `c-user-bucket` | `p3-user` | `p3-tickets-bucket` | https | GET signed URL · HTTPS | flow |
| `c-sweeper-firestore` / `c-sweeper-topic` | `p3-sweeper-*` | Firestore / topic | grpc | republish pending · gRPC | async |
| `c-ci-registry` | `p3-github-actions` | `p3-registry` | https | push image · HTTPS | async |
| `c-ci-run` | `p3-github-actions` | API Cloud Run | https | deploy canary · HTTPS | async |
| `c-chaos-run` | `p3-chaos` | API Cloud Run | https | break region · HTTPS | async |
| `c-user-api-denied` | `p3-user` | `p3-api-ew1` | https | — | flow, **denied**, `enforced_by`: ingress |

Routes broker (Noodle `route`) : `p3-topic-purchased` → `p3-sub-ew1` (subscription) ; `p3-topic-purchased` → `p3-sub-ew4` (subscription) ; `p3-sub-ew*` → `p3-topic-dlq` (dead-letter, après 5 livraisons) ; `p3-topic-purchased` → `p3-bq-sales` (subscription BigQuery, planned).

Références : `p3-armor` → `p3-glb` (targetRef) ; `p3-secrets` → `p3-api-*` (secretKeyRef) ; `p3-terraform` → tout ; `p3-monitoring` → `p3-glb` (SLO).

## 6. Flux à numéroter

### Vue `p3-topology` — « Comment un achat traverse la plateforme, et pourquoi une région peut tomber sans qu'on le voie ? »

Chemin nominal :
1. `c-user-glb` — l'acheteur poste sa commande
2. `c-glb-api-ew1` — le LB route vers la région saine la plus proche
3. `c-api-firestore` — transaction : stock, commande, billets `pending`
4. `c-api-topic` — publication de `ticket.purchased`
5. `c-sub-worker` — Pub/Sub pousse l'événement au worker
6. `c-worker-bucket` — le QR est écrit
7. `c-worker-firestore` — billet passé `issued`

Arrière-plan : A. sweepers ; B. CI (build → registry → canary) ; C. chaos nocturne ; D. SLO et alertes ; E. sauvegardes Firestore (PITR, quotidiennes).

### Vue `p3-purchase` (sequence) — « Que se passe-t-il entre le clic et le QR ? »

Avec les cas de retry : publication échouée → sweeper ; worker en erreur → nouvelle livraison ; double livraison (deux régions) → idempotence.

### Vue `p3-region-failover` (sequence) — « Que se passe-t-il quand europe-west1 tombe ? »

1. Les instances `api` de ew1 échouent leur readiness
2. Cloud Run *service health* (calculé à partir des readiness probes, nécessite ≥ 1 instance minimum par région) marque ew1 en mauvaise santé ; le LB global la retire
3. Le trafic part vers ew4, Firestore continue (multi-région, RPO 0)
4. Pub/Sub continue de livrer à `worker-ew4` ; `issue-ew1` accumule et rattrape au retour (doublons absorbés)
5. Retour automatique quand ew1 redevient saine
6. Aucune action humaine ; l'alerte est informative

## 7. Modes de défaillance

| Panne | Effet | Reprise | Humain ? |
|---|---|---|---|
| Une instance | Aucun | Remplacée par Cloud Run | Non |
| Une région | Latence un peu plus haute | Bascule et retour automatiques (RTO ≤ 1 min, RPO 0) | Non |
| Pic de charge | Plus d'instances | Scale-out jusqu'à `max_instances` | Non |
| Publication Pub/Sub perdue | Billet reste `pending` | Sweeper ≤ 7 min | Non |
| Worker en échec répété | Message en DLQ | Alerte, correction, rejeu | Oui, rare |
| Mauvaise version | Erreurs sur 10 % du trafic | Rollback automatique du canary | Non |
| Suppression accidentelle | Donnée perdue | PITR Firestore (≤ 1 min de perte) | Oui (décision) |
| Panne Firestore multi-région | Indisponibilité totale | Aucune côté projet (SLA Google 99,999 %) | Limite à citer en soutenance |
| Facture qui s'emballe (« denial of wallet ») | Coût | `max_instances`, Cloud Armor rate limit, alertes budget | Non |

## 8. Exploitation (SRE)

| Activité | P3 |
|---|---|
| Changement | PR + revue ; merge = déploiement canary automatique conditionné aux métriques |
| Incident | Alertes sur *burn rate* du SLO ; la plupart des pannes se réparent seules |
| DR | Test permanent (chaos nocturne), historique consultable |
| Patching | Rebuild hebdomadaire de l'image même sans changement de code |
| Secrets | Secret Manager, rotation sans redéploiement de code |

## 9. Coût indicatif (24/7)

LB global ≈ 20 $ + Cloud Armor ≈ 5–10 $ + reste majoritairement dans les offres gratuites à faible trafic. `min_instances = 1` par région est **obligatoire** pour la bascule automatique (service health) : compter de l'ordre de 10 $/mois par région, à mesurer. Fixer `max_instances` et des alertes budget.

## 10. Pour Noodle

Vues proposées : `p3-topology`, `p3-purchase` (sequence), `p3-region-failover` (sequence), `p3-access` (matrix : comptes de service × ressources), et une `landscape` commune.
Icônes manquantes à ajouter dans `.noodle/icons/` : `gcp`, `cloud-run`, `firestore`, `pubsub`, `cloud-storage`, `cloud-armor`, `cloud-cdn`, `bigquery`, `secret-manager`, `cloud-monitoring`, `artifact-registry`, `github-actions`, `opentelemetry`. Disponibles : `globe`, `user`, `python`, `fastapi`, `docker`, `terraform`, `trivy`.
Mapping kinds : LB/CDN = cloud, Cloud Armor/Secret Manager/IAM = security, api/worker/sweeper = backend, Firestore/buckets/BigQuery = database, topics/abonnements = bus (`pipe`), observabilité et delivery = tool.
