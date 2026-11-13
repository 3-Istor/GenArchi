# GenArchi — Génération Architecture

Projet pédagogique : concevoir une application web résiliente, la déployer en Platform 2 (P2) et Platform 3 (P3), puis expliquer les différences à partir de preuves observées.

## État après le premier coaching

Le [coaching du 3 novembre](docs/coaching/2026-11-03-restitution.md) retient une billetterie commune pour comparer les deux plateformes en situation de panne. Les schémas P2/P3 présentés sont des propositions. Le dépôt contient la documentation et les modèles de travail. L’application, les déploiements Terraform et les preuves de résilience restent à produire.

## Commencer ici

1. Lire le [cadrage et les questions ouvertes](docs/cadrage.md).
2. Consulter les [sources et leurs synthèses](docs/references/README.md).
3. Consulter le [compte rendu du 3 novembre](docs/coaching/2026-11-03-restitution.md) et la [préparation proposée pour le 17 novembre](docs/coaching/2026-11-17-preparation.md).
4. Consulter le [registre des décisions](docs/adr/README.md) avant de proposer une architecture.
5. Pour contribuer avec un agent, lire [AGENTS.md](AGENTS.md).

## Organisation du dépôt

```text
app/                  Application commune, à concevoir
infra/p2/             Infrastructure Terraform P2, à concevoir
infra/p3/             Infrastructure Terraform P3, à concevoir
tests/resilience/     Scénarios et relevés de preuves
docs/
  cadrage.md          Consignes, propositions, questions et jalons
  references/         Supports PowerPoint originaux et synthèses
  adr/                Registre et modèle de décision d’architecture
  coaching/           Préparations et restitutions de coaching
  comptes-rendus/     Comptes rendus des réunions d’équipe
```

## Prochaines étapes

- Définir le parcours minimal de billetterie et les données à préserver en cas de panne.
- Préciser les responsabilités de reprise, le périmètre Terraform et la faisabilité des deux architectures.
- Préparer un scénario de panne de données comparable sur P2 et P3, puis faire arbitrer le périmètre au prochain coaching.

## Vérification et contribution

La documentation est en français et utilise des liens relatifs. Une modification doit préserver la distinction entre consigne, proposition, décision et résultat mesuré. Aucun outil applicatif, commande de déploiement ou pipeline CI n’est encore défini. Les contrôles actuels portent sur les liens, les sources et la cohérence documentaire ; ils ne prouvent aucun fonctionnement applicatif ou cloud.
