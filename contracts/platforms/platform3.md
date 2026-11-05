# Contrat Platform 3 — « Born to be Cloud »

Contrat `0.2.0`, **proposition non validée**. Fournisseur : GCP ([ADR 0001](../../docs/adr/0001-fournisseur-gcp.md), accepté). Les seuils sont des cibles proposées, à confirmer avec Q-001. Ce que la Platform 3 promet à l'app, aux tests et au jury. Le *comment* est dans [`docs/architecture/platform3.md`](../../docs/architecture/platform3.md).

## 1. Positionnement

Colonne **« Born 2 be Cloud »** du cours (Cours 1, slide 10) : application conçue pour les briques cloud, **résilience applicative** (on suppose que tout tombe), multi-région, déploiement entièrement automatisé, exploitation **SRE / NoOps**. Architecture *event-driven* (Cours 4, slide 6).

## 2. Engagements de service (SLO, vérifiés par `contracts/tests/acceptance.md`)

| Indicateur | Cible P3 | Mesure |
|---|---|---|
| Modèle SLA | *Designed for failure, always on* | Cours 1, slide 9 |
| SLO disponibilité | 99,9 % des requêtes non-5xx sur 28 jours glissants | SLO Cloud Monitoring sur le LB |
| SLO latence | 95 % des `GET /events` < 300 ms | SLO Cloud Monitoring |
| Montée en charge | 500 utilisateurs virtuels en 60 s sans dépasser 1 % d'erreurs | T1 |
| Délai d'émission (I4) | p95 ≤ 10 s, p99 ≤ 60 s | Écart `purchased_at` → `issued_at` |
| Perte d'une instance | Aucune action humaine, remplacement automatique | T2 |
| Perte d'une région | **RTO ≤ 1 min** (bascule automatique), **RPO = 0** | T4 |
| Test de DRP permanent | Une région rendue indisponible 10 min **chaque nuit**, bascule et retour vérifiés automatiquement, historique conservé | Obligatoire (ADR 0004) : c'est ce qui distingue la colonne P3 de la colonne Cloud-Ready |
| Sauvegarde | Firestore PITR 7 jours + sauvegarde planifiée quotidienne (rétention 7 j) ; versioning du bucket | T7 |
| Mise en production | Canary 10 % pendant 5 min puis 100 %, rollback automatique si taux de 5xx > 2 % | T5 |
| Patching | Rebuild de l'image à chaque build et au moins chaque semaine | T6 |
| Reconstruction totale | `make p3-deploy` (OpenTofu + Cloud Build), sans étape manuelle | T8 |

## 3. Ce que la plateforme fournit à l'app

Voir la colonne P3 de [`runtime/app-runtime.md` § B](../runtime/app-runtime.md#b-ce-que-chaque-plateforme-doit-fournir). En résumé : services Cloud Run `api` et `worker` dans 2 régions, Firestore `eur3` (dont le trigger Eventarc « billet créé »), bucket Cloud Storage dual-région, topic Pub/Sub `ticket-issued` → BigQuery, secrets Secret Manager, logs et traces collectés automatiquement.

## 4. Contraintes de génération (non négociables)

La P3 **ne doit pas** utiliser :

- de VM (Compute Engine), de disque persistant, de groupe d'instances ;
- de stockage fichier partagé (NFS, Filestore) ;
- d'état local dans les instances ;
- de déploiement manuel (console ou `gcloud` à la main) : tout passe par OpenTofu et les cibles `make` (lancées depuis les postes de l'équipe ; une CI avec Workload Identity Federation reste à ajouter) ;
- de clé de service account exportée.

Ces interdits (sauf ceux qui relèvent du processus) sont vérifiés par `scripts/check_boundary.py` à partir de [`boundary.toml`](boundary.toml).

Attendu : au moins **2 régions actives**, données multi-région, communication asynchrone par événements, identité de service par composant (moindre privilège), WAF.

## 5. Interface OpenTofu (`infra/p3/`)

Entrées principales : `project_id`, `regions` (`["europe-west1", "europe-west4"]`, au moins 2), `firestore_location` (`eur3`), `storage_regions`, `domain` (`p3.genarchi.3istor.com`), `cloudflare_zone_id`, `app_image` (digest, écrit par `make p3-image`), `app_version`, `min_instances` (**≥ 1**, requis par *service health*), `max_instances` (plafond de coût), `chaos_enabled`, `chaos_schedule`, `chaos_unready_regions`, `alert_email`, `labels`. Détail : [`variables.tf`](../../infra/p3/variables.tf).

Sorties : `url`, `lb_ip`, `registry`, `image`, `regions`, `api_service`, `tickets_bucket`, `admin_token_secret`, `staff_token_secret`.

Cycle de vie : `make p3-deploy` décrit **toute** la plateforme, exploitation comprise (SLO, alertes, sauvegardes, planificateurs, test de panne). `make p3-canary` met une version en production, région par région, avec retour arrière automatique. La canary répartit le trafic avec `gcloud` ; OpenTofu ignore ce champ (`lifecycle.ignore_changes`).
