# ADR 0004 — P3 : test de DRP permanent et rollback automatique

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-001](../cadrage.md#registre-des-questions-ouvertes), [Q-002](../cadrage.md#registre-des-questions-ouvertes), [Q-010](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

Sans test de bascule permanent ni action automatique sur alerte, la P3 correspond à la colonne Cloud-Ready du [cours 1, diapositive 10](../references/originaux/cours-1-td-1.pptx), pas à « Born 2 be Cloud ». Le [cours 4, diapositive 48](../references/originaux/cours-4-p3-architecture-production.pptx) cite les « allers/retours perpétuels ».

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Chaos nocturne + rollback canary auto | Colonne 3 démontrée | Un workflow et une alerte de plus | P3 |
| Bascule auto seule | Plus simple | Reste en colonne 2 | Cloud-Ready |

## Décision proposée

Livrer un chaos nocturne qui rend une région indisponible 10 min et vérifie bascule et retour, et un canary avec rollback automatique (taux de 5xx > 2 %).

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

Ces éléments passent du niveau 2 (approfondissement) au MVP pour la P3. **Écart avec le [kickoff, diapositive 7](../references/originaux/kickoff.pptx)** à arbitrer.

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
