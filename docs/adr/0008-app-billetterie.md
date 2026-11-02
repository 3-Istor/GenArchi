# ADR 0008 — Application : billetterie, un seul code, deux jeux d'adaptateurs

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-006](../cadrage.md#registre-des-questions-ouvertes), [Q-007](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

Le kickoff propose une application commune et un même parcours ([diapositives 3 et 7](../references/originaux/kickoff.pptx)). L'app doit rendre visibles pic de charge, transaction, fichier et asynchrone.

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Billetterie | Pic à l'ouverture, stock transactionnel, QR asynchrone | Un peu plus de règles métier | Révèle bien P2/P3 |
| Partage de photos | Stockage et événements | Peu de transactions | Correct |
| Réservation de salles | Simple | Démo plate | Faible |

## Décision proposée

Billetterie d'événement (contrats dans [`contracts/`](../../contracts/README.md)). Backend de données, stockage et événements choisis par variables d'environnement.

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

Les tests de contrat tournent sur chaque combinaison d'adaptateurs : preuve que P2 et P3 servent la même app.

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
