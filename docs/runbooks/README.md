# Runbooks

En P2, **un humain décide et exécute** : chaque panne a sa procédure. En P3, le système se répare seul ; les runbooks P3 décrivent quoi regarder et quand intervenir.

Chaque procédure suit le même plan : *symptômes → diagnostic → action → vérification → retour à la normale*. Les commandes `make` se lancent depuis la racine du dépôt, dans l'environnement outillé (`nix develop` ou `mise`).

| Runbook | Quand |
|---|---|
| [`p2-deploy.md`](p2-deploy.md) | Premier déploiement, mise en production d'une version, patch des serveurs |
| [`p2-db.md`](p2-db.md) | Primaire PostgreSQL perdu, bascule planifiée, réintégration, restauration Barman |
| [`p2-nas.md`](p2-nas.md) | NAS actif perdu (les QR ne s'écrivent plus) |
| [`p2-zone.md`](p2-zone.md) | Perte d'un datacenter (zone) entier |
| [`p3-deploy.md`](p3-deploy.md) | Premier déploiement, canary, retour arrière |
| [`p3-incident.md`](p3-incident.md) | Alerte SLO, test de panne de région |

Toute action sur un environnement partagé (déploiement, destruction, injection de panne) demande l'accord de l'équipe pour cette action et cette cible.
