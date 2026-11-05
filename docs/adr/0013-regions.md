# ADR 0013 — Régions

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-004](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

Proximité utilisateurs (France), disponibilité des services, alignement sur Firestore eur3. Dépend de l'[ADR 0001](0001-fournisseur-gcp.md).

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| P2 europe-west9 ; P3 europe-west1 + europe-west4 | Paris pour P2 ; P3 sur les réplicas eur3 | Latence P3 un peu plus haute depuis la France | OK |
| Tout en europe-west9 | Simple | Pas de multi-région Firestore aligné | Faible en P3 |

## Décision proposée

P2 : europe-west9 zones a et b. P3 : europe-west1 et europe-west4. Projets séparés `genarchi-p2` et `genarchi-p3`.

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

Cloisonnement et lecture des coûts par plateforme.

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
