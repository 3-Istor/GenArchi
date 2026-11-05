# Scripts

| Script | Rôle | Commande vérifiée |
| --- | --- | --- |
| `check_boundary.py` | Vérifie qu'aucune ressource Terraform interdite par [`contracts/platforms/boundary.toml`](../contracts/platforms/boundary.toml) n'apparaît dans `infra/p2` ou `infra/p3`, modules locaux compris | `python3 scripts/check_boundary.py` |

Prérequis : Python 3.11 ou plus (module standard `tomllib`), aucune dépendance externe.
Code retour : `0` conforme, `1` violation, `2` configuration illisible. Vérifié le 2 novembre 2026 sur un jeu de fichiers Terraform de test (un cas conforme, deux violations dont une dans un module local) ; aucun Terraform réel n'existe encore. Pas encore branché en CI.
