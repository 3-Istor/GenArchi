# GenArchi — Génération Architecture

Projet pédagogique : concevoir une application web résiliente, la déployer en Platform 2 (P2) et Platform 3 (P3), puis expliquer les différences à partir de preuves observées.

## État au 2 novembre 2026

Le dépôt contient le cadrage, les sources et les modèles de travail. **Aucune application ni infrastructure n’est encore exécutable.** L’application, les technologies, les environnements et les critères détaillés restent à confirmer. Aucune décision technique n’est acceptée et aucun test de résilience n’a été exécuté.

Le cours demande une application web résiliente en P2 et P3, deux livrables Terraform et environ trois suivis suivis d’une soutenance. Le kickoff propose une démarche MVP et des jalons internes ; ces propositions ne constituent pas une validation du professeur.

## Commencer ici

1. Lire le [cadrage et les questions ouvertes](docs/cadrage.md).
2. Consulter les [sources et leurs synthèses](docs/references/README.md).
3. Préparer le [coaching du 3 novembre 2026](docs/coaching/2026-11-03-preparation.md).
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

- Faire préciser les critères de résilience, la distinction P2/P3 et le périmètre Terraform.
- Confirmer les environnements autorisés, les accès, le budget et les dates officielles.
- Choisir l’application et ses principes communs, puis consigner les choix validés dans les ADR.

Les questions sont suivies dans le cadrage pour éviter plusieurs listes divergentes. Les [coaching](docs/coaching/README.md) et [comptes rendus](docs/comptes-rendus/README.md) relient leurs conclusions à ces questions et aux ADR.

## Vérification et contribution

La documentation est en français et utilise des liens relatifs. Une modification doit préserver la distinction entre consigne, proposition, décision et résultat mesuré. Aucun outil applicatif, commande de déploiement ou pipeline CI n’est encore défini. Les contrôles actuels portent sur les liens, les sources et la cohérence documentaire ; ils ne prouvent aucun fonctionnement applicatif ou cloud.
