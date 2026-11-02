# Critères d'acceptation

Contrat `0.1.0`. Entrée de la prépa des tests. Deux niveaux :

1. **Tests de contrat** : fonctionnels, rapides, joués sur chaque combinaison d'adaptateurs (local postgres, local firestore, P2, P3). Ils prouvent que les deux plateformes servent **la même app**.
2. **Protocole T1–T8** : résilience et exploitation, joués sur P2 et P3 dans les mêmes conditions. Ils prouvent **la différence de génération**.

Variables communes aux scripts : `BASE_URL`, `ADMIN_TOKEN`, `STAFF_TOKEN`, `PLATFORM`.

## 1. Tests de contrat (fonctionnels)

| ID | Scénario | Attendu |
|---|---|---|
| C1 | Valider chaque réponse contre `contracts/api/openapi.yaml` | 100 % conformes (outil type Schemathesis ou validation de schéma dans les tests) |
| C2 | `GET /version` | `contract_version` = version de `contracts/README.md`, `platform` = cible testée |
| C3 | Créer un événement, l'acheter (2 billets) | `201`, 2 billets `pending`, `remaining` décrémenté de 2 |
| C4 | **Concurrence (I1)** : événement de capacité 100, 200 achats de 1 billet lancés en parallèle | Exactement 100 × `201` et 100 × `409 sold_out`, `remaining = 0`, 100 billets en base |
| C5 | **Idempotence achat (I2)** : même `Idempotency-Key` envoyée 5 fois en parallèle | 1 commande, stock décrémenté une fois, réponses `201` puis `200` avec le même `id` |
| C6 | Même clé, corps différent | `409 idempotency_conflict` |
| C7 | Sans `Idempotency-Key` | `400 idempotency_key_required` |
| C8 | **Émission (I4)** : après achat, sonder `GET /tickets/{id}` | Passe à `issued` sous le délai de la plateforme (P2 ≤ 15 min + durée batch, P3 ≤ 10 s p95) ; `GET /tickets/{id}/qr` → image PNG (directement ou après redirection) |
| C9 | **Scan (I3)** : scanner un billet `issued` deux fois | `200` puis `409 already_scanned` avec le même `scanned_at` |
| C10 | Scanner un billet `pending` | `409 ticket_not_issued` |
| C11 | Achat avant `sales_open_at` / après `starts_at` | `409 sales_not_open` / `409 event_closed` |
| C12 | Endpoints admin et staff sans jeton | `401 unauthorized` |
| C13 | **Émission idempotente (I5)** : rejouer 3 fois le même `ticket.purchased` (P3) ou relancer `issue-pending` (P2) | Un seul objet QR par billet, `issued_at` inchangé |

## 2. Protocole T1–T8 (résilience et exploitation)

Pendant T2 à T5, un **trafic de fond k6** tourne : 20 utilisateurs virtuels (`GET /events` + 1 achat toutes les 5 s chacun). Ce trafic sert de sonde : tout échec compte dans la disponibilité mesurée.

Pour chaque test, on enregistre : heure de début de la panne, heure de détection, heure de retour au nominal, requêtes en erreur (k6), **nombre d'actions humaines** (chaque commande tapée ou clic compte pour 1), données perdues.

| ID | Scénario | Déclenchement P2 | Déclenchement P3 | Succès P2 | Succès P3 |
|---|---|---|---|---|---|
| T1 | Ouverture des ventes | k6 : 0 → 500 VU en 60 s, palier 3 min, événement de capacité 5 000 | idem | Mesurer le point de saturation (p95 > 1 s ou erreurs > 1 %). Aucune survente | Erreurs < 1 %, p95 `GET /events` < 300 ms, aucune survente, instances > 1 par région |
| T2 | Perte d'une instance applicative | `gcloud compute instances stop app-01` | `POST /internal/chaos {"mode":"crash"}` répété sur plusieurs instances | Trafic servi par `app-02` après ≤ 10 s ; `app-01` relancée **à la main** | Aucune action humaine, erreurs < 1 % |
| T3 | Perte de la base primaire | `gcloud compute instances stop db-01` | Sans objet (Firestore multi-région) : montrer le SLA et l'absence de serveur | RTO ≤ 30 min, RPO ≤ 5 min, runbook suivi | N/A, justifier |
| T4 | Perte d'une zone / région | Arrêter toutes les VM de la zone a | Workflow CI `chaos-region` : redéploie le service `api` de `europe-west1` avec `CHAOS_FORCE_UNREADY=true` (toutes ses instances répondent 503 sur `/readyz`), puis le remet | RTO ≤ 30 min, RPO ≤ 5 min | Bascule automatique, RTO ≤ 1 min, RPO = 0, retour automatique |
| T5 | Mise en production d'une v2 | Runbook de déploiement VM par VM | Pipeline CI : canary 10 % → 100 % | Indisponibilité mesurée, rollback = runbook | 0 erreur visible ; une v2 volontairement cassée revient en arrière **automatiquement** |
| T6 | Correction d'une faille OS | `apt upgrade` sur chaque VM | Rebuild de l'image + redéploiement | Durée et nb d'actions mesurés | Durée et nb d'actions mesurés, 0 action sur les instances |
| T7 | Suppression accidentelle d'un événement | Restauration du dernier `pg_dump` | Restauration PITR Firestore à T-1 min | Données retrouvées, perte ≤ depuis le dernier dump | Données retrouvées, perte ≤ 1 min |
| T8 | Reconstruction totale | `terraform destroy` puis `apply` + Ansible + runbooks | `terraform destroy` puis `apply` + pipeline | Durée jusqu'au premier billet vendu, nb d'actions | Durée, 0 étape manuelle après `apply` |

## 3. Tableau de scores (sortie attendue de la campagne)

| Indicateur | P2 | P3 |
|---|---|---|
| Disponibilité mesurée sur T2–T5 (requêtes OK / total) | | |
| RTO / RPO observés (T3, T4) | | |
| Nombre total d'actions humaines (T2–T8) | | |
| Point de saturation (T1) | | |
| Durée de reconstruction (T8) | | |
| Coût mensuel réel (facture, labels `platform`) | | |
| Lignes de Terraform / lignes de runbook | | |

## 4. Hooks fournis par l'app pour les tests

- `GET /version` : quelle instance, zone ou région a répondu (preuve de bascule).
- `POST /internal/chaos` (`crash`, `unready`, `latency`) : actif seulement avec `CHAOS_ENABLED=true`.
- `GET /admin/events/{id}/stats` : compteurs pour vérifier I1 sans accès direct à la base.
