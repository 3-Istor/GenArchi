# ADR 0016 — P3 : l'événement « billet créé » est émis par Firestore

- Statut : proposé
- Date de proposition : 2026-11-04
- Auteur(s) : Brian Perret (tech lead), avec l'assistant IA
- Questions concernées : sans objet
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : complète la proposition [0011](0011-p3-sweeper.md) (le sweeper devient un filet, plus le mécanisme principal)

## Contexte

En v0.1, l'API écrivait la commande dans Firestore puis publiait `ticket.purchased` sur Pub/Sub. Si l'instance meurt entre les deux, l'événement est perdu (double écriture) : d'où le sweeper.

## Options étudiées

| Option | Avantages | Limites |
| --- | --- | --- |
| API publie après commit | Simple | Double écriture : perte possible |
| Outbox + relais | Exact | Un composant de plus à exploiter |
| **Trigger Firestore → Eventarc** | La base émet l'événement quand le document est créé : pas de double écriture | Livraison « au moins une fois » : le traitement doit être idempotent |

## Décision proposée

Trigger Eventarc `google.cloud.firestore.document.v1.created` sur `tickets/{ticket}` (base `eur3`), un trigger par région vers le worker de cette région. L'émission est idempotente (invariant I5), donc les doublons sont sans effet. Le worker publie `ticket.issued` sur Pub/Sub, qui alimente BigQuery. Le rattrapage `issue-pending` reste planifié toutes les 5 min.

## Conséquences

L'API P3 n'a plus de dépendance à Pub/Sub ; contrat d'exécution 0.2.0 (`EVENTS_BACKEND=none` côté API).

## Validation et suivi

Billet émis en quelques secondes sur GCP ; une région coupée n'arrête pas l'émission. Non encore exécuté.

## Références

[`infra/p3/run.tf`](../../infra/p3/run.tf), [contrat d'exécution](../../contracts/runtime/app-runtime.md).
