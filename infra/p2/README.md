# Infrastructure Platform 2

Emplacement réservé au futur livrable Terraform P2. Aucun fichier Terraform ni environnement déployable n’est présent.

Piste du [kickoff, diapositive 4](../../docs/references/originaux/kickoff.pptx) : infrastructure virtualisée, instances applicatives redondées, équilibrage de charge et persistance dont la bascule reste à définir. Cette piste n’est pas une architecture acceptée.

Avant implémentation, confirmer l’environnement, les accès et coûts, la distinction attendue P2/P3, le périmètre Terraform et la stratégie de données : [Q-002 à Q-004 et Q-009](../../docs/cadrage.md). Formaliser les choix dans les [ADR](../../docs/adr/README.md).

Documenter ensuite prérequis, paramètres, gestion sécurisée de l’état Terraform, déploiement, vérifications et remise en état/destruction. Garder les secrets et états hors Git ; versionner le futur fichier de verrouillage des providers. Les [tests de résilience](../../tests/resilience/README.md) devront produire des preuves sur une cible autorisée.
