# ADR 0012 — P2 : supervision Zabbix

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-002](../cadrage.md#registre-des-questions-ouvertes), [Q-010](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer ; avis favorable du chantier P2 le 2026-11-03 ([CR](../comptes-rendus/2026-11-03-seance-p2.md)), validation de l’équipe à venir
- Remplace / remplacée par : sans objet

## Contexte

La supervision fait partie de la génération : [cours 4, diapositives 23–25](../references/originaux/cours-4-p3-architecture-production.pptx) (agents, push/pull, Nagios/Zabbix/Centreon).

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Zabbix sur VM | Outil cité, agents push/pull | Une VM de plus, non supervisée elle-même | P2 |
| Cloud Monitoring + Ops Agent | Rapide | Peu typé P2 | Plutôt P3 |

## Décision proposée

Zabbix 7 sur `mon-01`, agents sur toutes les VM, alertes envoyées sur un webhook Discord (URL secrète, hors dépôt), traitement humain. Modifié le 2026-11-03 : le mail est remplacé par Discord ([CR](../comptes-rendus/2026-11-03-seance-p2.md)).

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

Limite P2 à citer : personne ne surveille le superviseur.

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
