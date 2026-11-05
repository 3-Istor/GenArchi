# ADR 0005 — P3 : Firestore multi-région eur3

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-007](../cadrage.md#registre-des-questions-ouvertes), [Q-009](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

Le [cours 3](../references/originaux/cours-3-p2-middleware.pptx) associe NoSQL et DBaaS à la P3. Un scale-out serverless sature vite une base SQL en connexions.

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Firestore eur3 | Multi-région, RPO 0, quasi gratuit | Pas de jointures ; second adaptateur à écrire | P3 |
| Cloud SQL PostgreSQL HA | Même SQL qu'en P2 | ~100 $/mois, régional, connexions limitées | Plutôt Cloud-Ready |

## Décision proposée

Firestore natif en `eur3`, régions Cloud Run alignées sur ses réplicas (europe-west1, europe-west4).

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

Deux adaptateurs (PostgreSQL P2, Firestore P3) testés par les mêmes tests de contrat.

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
