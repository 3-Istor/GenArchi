# ADR 0009 — P2 : sauvegarde par pg_dump et snapshots de disques

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-009](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer ; avis favorable du chantier P2 le 2026-11-03 ([CR](../comptes-rendus/2026-11-03-seance-p2.md)), validation de l’équipe à venir
- Remplace / remplacée par : sans objet

## Contexte

Le [cours 1, diapositive 10](../references/originaux/cours-1-td-1.pptx) place les snapshots en Cloud-Ready, mais le [cours 2, diapositive 34](../references/originaux/cours-2-p2-infra.pptx) les présente comme fonction d'une baie de stockage P2.

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| pg_dump + snapshots | Double protection, justifiable | Écart discutable | P2 (baie) |
| pg_dump seul | Puriste | Restauration plus lente | P2 |

## Décision proposée

`pg_dump` quotidien 02:00 vers NFS (7 j) et snapshots quotidiens des disques `db-*` et `nfs-01` (7 j). Contrôle quotidien manuel.

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

Restauration toujours manuelle (runbooks).

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
