# Spec d'architecture — Platform 3 « Born to be Cloud »

> Version 0.2, **proposée**. Implémentée dans [`infra/p3/`](../../infra/p3/README.md) ; validée statiquement (`tofu validate`), pas encore déployée. Engagements : [contrat P3](../../contracts/platforms/platform3.md).

## 1. Principe

On suppose que tout tombe : une instance, une zone, une région. L'application est faite de **services sans état** dans deux régions actives, les données sont **multi-région**, les traitements sont **déclenchés par des événements**, et c'est le système qui bascule, déploie et revient en arrière. L'humain observe des SLO.

## 2. Régions

| Région | Rôle |
|---|---|
| `europe-west1` (Belgique) | Active : API, worker, jobs ; cible du test de panne nocturne |
| `europe-west4` (Pays-Bas) | Active : API, worker, jobs |
| `eur3` (Belgique + Pays-Bas, témoin en Finlande) | Firestore multi-région, réplication synchrone |
| `EU` dual-région `EUROPE-WEST1` + `EUROPE-WEST4` | Bucket des QR, réplication turbo (RPO 15 min garanti, quasi immédiat en pratique) |

Les régions Cloud Run sont alignées sur les réplicas en lecture-écriture de `eur3` : la latence vers la base est la même des deux côtés.

## 3. Composants

| Composant | Service | Résilience |
|---|---|---|
| Entrée | LB HTTP(S) **global** (anycast), certificat géré, redirection HTTP → HTTPS | Envoie vers la région saine la plus proche |
| Sécurité | Cloud Armor : règles OWASP préconfigurées (SQLi, XSS), 600 req/min/IP | En bordure, avant toute instance |
| Front | Bucket + Cloud CDN | Statique, mis en cache |
| API | Cloud Run `p3-api`, 2 régions, 1 à 20 instances, sonde de readiness `/readyz` | *Service health* : une région qui échoue sa readiness sort du LB |
| Worker | Cloud Run `p3-worker`, 2 régions, entrée interne seulement | Chaque région reçoit les événements ; émission idempotente |
| Base | Firestore `(default)` `eur3`, PITR 7 j, sauvegarde quotidienne 7 j, protection contre la suppression | Multi-région, RPO 0 |
| Stock | Compteurs répartis (*shards*) et mise à jour sans verrou (comparaison de date de mise à jour) | Pas de document chaud sous forte charge |
| Événement « billet créé » | Trigger Eventarc Firestore `document.v1.created` → worker ([ADR 0016](../adr/0016-p3-evenement-emis-par-firestore.md)) | Livraison au moins une fois, relivraison en cas d'échec |
| QR | GCS dual-région, versionné, accès public interdit, URL signées (signBlob, sans clé) | Multi-région |
| Analyse | Pub/Sub `ticket-issued` → abonnement BigQuery | Remplace l'export nocturne |
| Rattrapage | Cloud Run job `p3-issue-pending`, Cloud Scheduler toutes les 5 min, dans chaque région | Filet de sécurité |
| Test de panne | Job `p3-chaos-region`, chaque nuit : API de `europe-west1` « non prête » 10 min ([ADR 0004](../adr/0004-p3-drp-permanent-rollback-auto.md)) | Preuve permanente du PRA |
| Mise en production | `make p3-canary` : 10 % → observation → 100 %, ou retour arrière automatique | Aucun humain dans la boucle |
| Observabilité | Logs JSON corrélés à la trace, sonde externe, SLO 99,9 %, alerte burn rate | — |
| Secrets | Secret Manager, réplication automatique | — |

### Identités (moindre privilège)

| Compte | Droits |
|---|---|
| `p3-api` | Firestore (lecture-écriture), lecture des QR, signature de ses propres URL, secrets |
| `p3-worker` | Firestore, écriture des QR, publication `ticket-issued`, secrets |
| `p3-events` | Réception Eventarc, invocation du worker |
| `p3-scheduler` | Lancement des jobs |
| `p3-chaos` | Modifier l'API (révision), agir en tant que `p3-api` |

## 4. Parcours d'un achat

1. Le LB global reçoit la requête, Cloud Armor la filtre, elle part vers l'API de la région saine la plus proche.
2. L'API réserve les places (shards de stock) et crée commande + billets dans une seule écriture atomique.
3. Firestore émet « document billet créé » ; Eventarc l'apporte au worker de chaque région.
4. Le worker génère le QR, l'écrit dans GCS, marque le billet émis (une seule fois), publie `ticket.issued` → BigQuery.

## 5. Modes de défaillance

| Panne | Effet | Qui agit | RTO / RPO |
|---|---|---|---|
| Instance | Remplacée | Cloud Run | secondes / 0 |
| Zone | Invisible (Cloud Run est régional) | Google | 0 / 0 |
| Région (ou API d'une région en erreur) | Trafic envoyé à l'autre région | LB + service health | ≤ 1 min / 0 |
| Livraison d'événement perdue | Billet émis par le rattrapage | Job planifié | ≤ 5 min / 0 |
| Mauvaise version | Retirée pendant la canary | Script canary | ≤ 5 min / 0 |
| Erreur humaine (données) | — | PITR Firestore, versions GCS | minutes / 0 |
| Attaque applicative, rafale | Bloquée en bordure | Cloud Armor | — |

## 6. Exploitation (SRE)

Budget d'erreur : 0,1 % des requêtes sur 28 jours. Alerte si le budget brûle 10 fois trop vite sur 1 h. Runbooks : [`p3-deploy.md`](../runbooks/p3-deploy.md), [`p3-incident.md`](../runbooks/p3-incident.md).

## 7. Coût indicatif (24/7)

2 × 1 instance minimale (CPU alloué à la requête), LB global, politique Cloud Armor, Firestore et GCS de faible volume : de l'ordre de **50 à 80 $ par mois**. À vérifier dans le simulateur.

## 8. Écarts avec la v0.1

L'API ne publie plus d'événement (Firestore l'émet) ; topic `ticket-purchased` supprimé ; stock réparti en shards avec mise à jour sans verrou ; front sur CDN ; seuils SLO et canary repris du contrat.
