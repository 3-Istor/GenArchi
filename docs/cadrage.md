# Cadrage du projet

État documentaire au **2 novembre 2026**. Aucune décision technique acceptée. Les [sources](references/README.md) sont conservées avec leurs synthèses pour rendre les propositions vérifiables.

## Consignes identifiées dans le cours

Le [cours 1, diapositive 5](references/originaux/cours-1-td-1.pptx) demande :

- Une application web résiliente en Platform 2 et Platform 3.
- Deux livrables Terraform, un par plateforme.
- Environ trois suivis et une soutenance finale.

Cette diapositive ne fixe pas l’application, le fournisseur, le budget, les dates officielles ou des seuils chiffrés de résilience. Ces éléments restent à confirmer, sans les déduire des exemples techniques.

## Propositions du kickoff

Le [kickoff](references/originaux/kickoff.pptx), daté du 1er novembre 2026 et présenté comme proposition de travail, suggère :

- Une application commune et un même parcours fonctionnel sur les deux plateformes (diapositives 3 et 7).
- Un MVP comprenant les deux déploiements reproductibles, au moins un scénario de panne vérifié par plateforme et une comparaison appuyée sur les preuves (diapositive 7).
- Une conception commune, puis deux réalisations en parallèle ; six personnes réparties en un PM, deux Tech Leads et trois collaborateurs transverses (diapositive 8). Noms et affectations à confirmer.
- Des approfondissements après le MVP : autres pannes, observabilité enrichie, CI/CD et mesures complémentaires (diapositive 7). Ils ne sont pas des engagements acquis.

## Différencier P2 et P3

| Axe | P2 : orientation à étudier | P3 : orientation à étudier |
| --- | --- | --- |
| Calcul | Infrastructure virtualisée, composants redondés | Instances remplaçables, services cloud possibles |
| Disponibilité | Bascule et opérations maîtrisées | Retrait d’instance et réparation automatisée |
| État applicatif | Persistance et réplication à concevoir | Processus sans état et données externalisées à étudier |
| Démonstration proposée | Perte d’une VM applicative, trafic vers la seconde | Perte d’une instance, remplacement automatique |

Sources : [cours 1, diapositives 8 et 10](references/originaux/cours-1-td-1.pptx), [cours 4, diapositives 13–17 et 31](references/originaux/cours-4-p3-architecture-production.pptx), [kickoff, diapositives 4–6](references/originaux/kickoff.pptx). Ce tableau décrit des pistes, pas une architecture sélectionnée. Une DB répliquée, des conteneurs ou des microservices ne sont pas automatiquement imposés.

## Jalons internes proposés

Source : [kickoff, diapositives 1, 9 et 10](references/originaux/kickoff.pptx). **Ces dates ne sont pas des échéances officielles confirmées.**

| Date 2026 | Intention interne | État |
| --- | --- | --- |
| 3 novembre | Coaching et clarification du cadrage | Préparation disponible ; tenue à confirmer |
| 15 novembre | Architectures validées | Cible proposée |
| 29 novembre | Deux déploiements | Cible proposée |
| 6 décembre | MVP résilient et preuves | Cible proposée |
| 15 décembre | Démonstration | Cible interne proposée |

## Registre des questions ouvertes

Conserver les identifiants lors des mises à jour. Toutes les questions ci-dessous sont **ouvertes**, avec responsable et échéance **à confirmer**. Pour clore une question, ajouter la réponse, sa date et un lien vers la restitution, le CR ou l’ADR qui la justifie. Ne pas supprimer son historique.

| ID | Question | Trace de réponse |
| --- | --- | --- |
| Q-001 | Quels scénarios de panne et critères observables sont attendus ? Quels seuils de reprise ou de perte de données, s’il y en a ? | À confirmer |
| Q-002 | Quelles différences minimales doivent distinguer P2 de P3 ? | À confirmer |
| Q-003 | Jusqu’où Terraform doit-il couvrir le provisionnement, la configuration et le déploiement applicatif ? | À confirmer |
| Q-004 | Quels environnements et services sont autorisés ? Quels accès, quotas et budget sont disponibles ? AWS et OpenStack sont des pistes du kickoff. | À confirmer |
| Q-005 | Quels critères d’évaluation, dates officielles et formats de suivi/soutenance sont retenus ? | À confirmer |
| Q-006 | Quelle application, quel parcours minimal et quelles données persistantes choisir ? | À confirmer |
| Q-007 | Quelles technologies et interfaces communes retenir pour les deux déploiements ? | À confirmer |
| Q-008 | Qui occupe les rôles proposés et qui porte chaque action ? | À confirmer |
| Q-009 | Quels mécanismes de persistance, sauvegarde et reprise retenir sur chaque plateforme ? | À confirmer |
| Q-010 | Quel protocole de mesure et quelles preuves conserver pour comparer les plateformes ? | À confirmer |

## Décisions et état des livrables

Le [registre ADR](adr/README.md) est vide. Les modèles et emplacements sont prêts ; application, infrastructures et tests restent à réaliser après validation des choix. La [préparation du premier coaching](coaching/2026-11-03-preparation.md) reprend les questions prioritaires et les propositions à discuter.
