# Infrastructure Platform 3

Emplacement réservé au futur livrable Terraform P3. Aucun fichier Terraform ni environnement déployable n’est présent.

Piste du [kickoff, diapositive 5](../../docs/references/originaux/kickoff.pptx) : instances remplaçables, données externalisées, contrôles de santé et reprise automatisée. Fournisseur, conteneurs et mécanismes de réparation restent à choisir ; aucun orchestrateur n’est imposé.

Avant implémentation, confirmer l’environnement, les services autorisés, les accès et coûts, le périmètre Terraform et les critères d’auto-reprise : [Q-001 à Q-004 et Q-009](../../docs/cadrage.md). Formaliser les choix dans les [ADR](../../docs/adr/README.md).

Documenter ensuite prérequis, paramètres, gestion sécurisée de l’état Terraform, déploiement, vérifications et remise en état/destruction. Garder les secrets et états hors Git ; versionner le futur fichier de verrouillage des providers. Les [tests de résilience](../../tests/resilience/README.md) devront observer le comportement effectif et la réparation.
