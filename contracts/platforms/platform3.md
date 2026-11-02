# Contrat Platform 3 — « Born to be Cloud »

Contrat `0.1.0`, **proposition non validée** (fournisseur : [ADR 0001](../../docs/adr/0001-fournisseur-gcp.md), proposé). Les seuils sont des cibles proposées, à confirmer avec Q-001. Ce que la Platform 3 promet à l'app, aux tests et au jury. Le *comment* est dans [`docs/architecture/platform3.md`](../../docs/architecture/platform3.md).

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
| Reconstruction totale | `terraform apply` + pipeline, sans étape manuelle | T8 |

## 3. Ce que la plateforme fournit à l'app

Voir la colonne P3 de [`runtime/app-runtime.md` § B](../runtime/app-runtime.md#b-ce-que-chaque-plateforme-doit-fournir). En résumé : services Cloud Run `api` et `worker` dans 2 régions, Firestore `eur3`, bucket Cloud Storage, topics Pub/Sub, secrets Secret Manager, logs et traces collectés automatiquement.

## 4. Contraintes de génération (non négociables)

La P3 **ne doit pas** utiliser :

- de VM (Compute Engine), de disque persistant, de groupe d'instances ;
- de stockage fichier partagé (NFS, Filestore) ;
- d'état local dans les instances ;
- de déploiement manuel (console ou `gcloud` à la main) : tout passe par Terraform et la CI ;
- de clé de service account exportée (la CI utilise Workload Identity Federation).

Ces interdits (sauf ceux qui relèvent du processus) sont vérifiés en CI à partir de [`boundary.toml`](boundary.toml).

Attendu : au moins **2 régions actives**, données multi-région, communication asynchrone par événements, identité de service par composant (moindre privilège), WAF.

## 5. Interface Terraform (`infra/p3/`)

### Entrées

| Variable | Type | Défaut | Rôle |
|---|---|---|---|
| `project_id` | string | — | Projet GCP dédié P3 |
| `regions` | list(string) | `["europe-west1", "europe-west4"]` | Régions actives (≥ 2) |
| `firestore_location` | string | `eur3` | Multi-région Firestore |
| `name_prefix` | string | `p3` | Préfixe des ressources |
| `api_image` | string | — | Image (digest) déployée, fournie par la CI |
| `canary_percent` | number | `0` | Part de trafic vers la révision candidate |
| `min_instances` | number | `1` | Minimum par région pour `api`. **≥ 1 obligatoire** : Cloud Run service health en a besoin pour calculer la santé et basculer |
| `max_instances` | number | `20` | Plafond de coût par région |
| `domain` | string | `null` | Si défini : certificat managé + enregistrement DNS |
| `alert_email` | string | — | Notifications SLO |
| `labels` | map(string) | `{ platform = "p3", project = "genarchi" }` | Appliqués partout |

### Sorties

| Sortie | Contenu |
|---|---|
| `base_url` | URL publique (LB global) |
| `lb_ip` | IP anycast |
| `api_services` | map région → URL Cloud Run (non exposée publiquement) |
| `tickets_bucket` | Nom du bucket |
| `topics` | Noms des topics |
| `ci_service_account` | Compte utilisé par la CI via WIF |

### Cycle de vie

`terraform apply` décrit **toute** la plateforme, exploitation comprise (SLO, alertes, sauvegardes, planificateurs). La CI construit l'image et met à jour `api_image` / `canary_percent`. Aucune étape manuelle entre `apply` et le premier billet vendu.
