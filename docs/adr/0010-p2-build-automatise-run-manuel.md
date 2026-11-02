# ADR 0010 — P2 : build automatisé, run manuel

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-002](../cadrage.md#registre-des-questions-ouvertes), [Q-003](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

Le livrable impose Terraform ([cours 1, diapositive 5](../references/originaux/cours-1-td-1.pptx)). L'automatisation du déploiement (« Puppet-like ») relève de la colonne Cloud-Ready.

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Build auto, run manuel | Respecte le livrable et la génération | Runbooks à écrire | P2 |
| Tout automatisé (Ansible pour le run) | Plus rapide | Colonne Cloud-Ready / DevOps | Hors P2 |

## Décision proposée

Terraform et Ansible servent uniquement à construire la plateforme et à l'installation initiale. Mise en prod, patch, bascule, restauration et resize sont des runbooks exécutés à la main après une demande de changement approuvée.

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

Les runbooks sont un livrable de la P2 ; le nombre d'actions humaines est mesuré (Q-010).

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
