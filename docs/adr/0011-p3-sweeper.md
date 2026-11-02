# ADR 0011 — P3 : rattrapage des publications perdues par un sweeper

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-007](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

L'API écrit en base puis publie sur Pub/Sub : si la publication échoue, le billet reste `pending`.

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Sweeper (Cloud Run job /5 min) | Simple, idempotent | Ressemble à un batch | P3 si filet de réconciliation |
| Trigger Eventarc sur création Firestore | Supprime la double écriture | Support eur3 à vérifier | P3 |

## Décision proposée

Sweeper en v1 dans chaque région ; Eventarc à évaluer.

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

À expliquer en soutenance : le sweeper n'est pas un traitement métier.

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
