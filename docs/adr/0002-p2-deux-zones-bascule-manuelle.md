# ADR 0002 — P2 : deux zones, bascule manuelle

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-001](../cadrage.md#registre-des-questions-ouvertes), [Q-002](../cadrage.md#registre-des-questions-ouvertes), [Q-009](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer ; avis favorable du chantier P2 le 2026-11-03 ([CR](../comptes-rendus/2026-11-03-seance-p2.md)), validation de l’équipe à venir
- Remplace / remplacée par : sans objet

## Contexte

Le [cours 1, diapositive 10](../references/originaux/cours-1-td-1.pptx) place « mono-AZ, DRP manuel » en P2 et « dual-AZ, DRP automatisé » en Cloud-Ready. Le TD demande une application résiliente ; le [kickoff, diapositive 4](../references/originaux/kickoff.pptx) propose 2 VM web/app, une base primaire et une réplique.

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Deux zones, bascule manuelle | Fidèle à une entreprise à deux salles ([cours 2](../references/originaux/cours-2-p2-infra.pptx) : « 2 DC ou 1 Dual-DC »), résilience démontrable | Bascule DB humaine, RTO ~30 min | P2 tant que la bascule reste manuelle |
| Une zone | Strictement conforme au tableau du cours | Résilience faible, perte de zone = arrêt | P2 |
| Deux zones, bascule auto (Patroni…) | RTO court | DRP automatisé = colonne Cloud-Ready | Hors P2 |

## Décision proposée

Deux zones d'europe-west9 ; web et app actifs dans les deux ; PostgreSQL primaire en zone a, réplique asynchrone en zone b ; **toute bascule est manuelle** (runbook).

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

NFS, batch et supervision restent des SPOF assumés. Détail : [spec P2](../architecture/platform2.md), [challenge §2](../architecture/challenge.md).

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
