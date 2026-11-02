# ADR 0006 — P2 : équipements réseau managés

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-002](../cadrage.md#registre-des-questions-ouvertes), [Q-004](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

Un DC P2 a des appliances (LB, passerelle internet, DNS, accès d'administration) ; [cours 2, diapositives 24–25](../references/originaux/cours-2-p2-infra.pptx). Les reproduire en VM sur GCP est coûteux et fragile (IP flottante non native).

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| LB régional, Cloud NAT, Cloud DNS privé, tunnel IAP | Simple, fiable, sans autoscaling | Moins « DC » visuellement | P2 (équivalents d'appliances) |
| HAProxy en VM + bastion à IP publique | Plus fidèle | IP flottante délicate, plus de VM | P2 |

## Décision proposée

Services réseau managés régionaux, sans remédiation automatique ; bastion VM joint par tunnel IAP.

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

Écart assumé, à présenter en soutenance.

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
