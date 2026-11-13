# Cadrage du projet

État documentaire au **13 novembre 2026**, après le premier coaching. La billetterie commune est retenue comme cas d’étude. Les choix d’architecture restent à arbitrer. Les [sources](references/README.md) sont conservées avec leurs synthèses pour rendre les propositions vérifiables.

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

## Retours du premier coaching

Le [compte rendu du 3 novembre](coaching/2026-11-03-restitution.md) rapporte que les enseignants ont validé le principe d’une application et de fonctionnalités métier communes. Ils attendent une comparaison observable de la reprise. Le choix des pannes et les objectifs RTO/RPO sont à justifier par le métier. La panne de base de données a été discutée et une supervision complète n’est pas explicitement exigée.

Le [support présenté](coaching/2026-11-03-coaching-1.pptx) décrit deux propositions. En P2, l’équipe exploite les VM et les middlewares avec une bascule de base automatisée et certaines remises en état manuelles (diapositives 3 et 5). En P3, l’équipe envisage une application sans état sur deux régions actives et des services GCP managés (diapositives 4 et 5). La portée géographique des services et le comportement des dépendances restent à vérifier (Q-002, Q-004, Q-009). La bascule automatique de la base P2 figurant dans le support nuance le résumé du CR sur les interventions manuelles. Le prochain coaching doit préciser qui détecte, bascule et répare, composant par composant (Q-002).

Les mentions « zéro perte », « < 1 min » et « testée chaque nuit » dans les diapositives 3 à 5 décrivent des hypothèses ou des intentions à vérifier (Q-001, Q-009, Q-010). La [synthèse des diapositives](references/syntheses.md#premier-coaching) détaille les propositions.

## Jalons internes proposés

Source : [kickoff, diapositives 1, 9 et 10](references/originaux/kickoff.pptx). **Ces dates ne sont pas des échéances officielles confirmées.**

| Date 2026 | Intention interne | État |
| --- | --- | --- |
| 3 novembre | Coaching et clarification du cadrage | Tenu, [compte rendu disponible](coaching/2026-11-03-restitution.md) |
| 15 novembre | Architectures validées | Cible proposée |
| 17 novembre | Prochain coaching indiqué par l’équipe | [Préparation proposée](coaching/2026-11-17-preparation.md) |
| 29 novembre | Deux déploiements | Cible proposée |
| 6 décembre | MVP résilient et preuves | Cible proposée |
| 15 décembre | Démonstration | Cible interne proposée |

Le CR mentionne une échéance au **12 janvier** (2027 probable). L’année, la nature de l’échéance et le calendrier officiel sont à confirmer (Q-005). Le 15 décembre correspond à la cible interne du kickoff.

## Registre des questions

Conserver les identifiants lors des mises à jour. Les précisions du [coaching du 3 novembre](coaching/2026-11-03-restitution.md) sont reportées ci-dessous. Les points indiqués comme restant à préciser sont ouverts. Responsables et échéances à confirmer. Pour clore une question, ajouter la réponse, sa date et un lien vers la restitution, le CR ou l’ADR qui la justifie. Ne pas supprimer son historique.

| ID | Question | Trace de réponse |
| --- | --- | --- |
| Q-001 | Quels scénarios de panne et critères observables sont attendus ? Quels seuils de reprise ou de perte de données, s’il y en a ? | Scénarios libres et objectifs de reprise à justifier par le métier (CR §4–5). Scénarios et seuils à choisir. |
| Q-002 | Quelles différences minimales doivent distinguer P2 de P3 ? | Comparer les responsabilités d’exploitation et la reprise réelle (CR §2, §3 et §6). Place des bascules automatiques et services managés en P2 à préciser. |
| Q-003 | Jusqu’où Terraform doit-il couvrir le provisionnement, la configuration et le déploiement applicatif ? | À confirmer |
| Q-004 | Quels environnements et services sont autorisés ? Quels accès, quotas et budget sont disponibles ? AWS et OpenStack sont des pistes du kickoff. | GCP envisagé, notamment pour les crédits (CR §3). Fournisseur, crédits utilisables, accès, quotas et portée des services à vérifier. |
| Q-005 | Quels critères d’évaluation, dates officielles et formats de suivi/soutenance sont retenus ? | Comparaison étayée par des preuves attendue. Échéance du 12 janvier évoquée (CR §4 et §9). Date complète, barème et format à confirmer. |
| Q-006 | Quelle application, quel parcours minimal et quelles données persistantes choisir ? | Billetterie commune retenue pour l’étude (CR §1). Achat, QR code et scan unique proposés (support, diapositive 2). Périmètre MVP et données à préciser. |
| Q-007 | Quelles technologies et interfaces communes retenir pour les deux déploiements ? | À confirmer |
| Q-008 | Qui occupe les rôles proposés et qui porte chaque action ? | À confirmer |
| Q-009 | Quels mécanismes de persistance, sauvegarde et reprise retenir sur chaque plateforme ? | Résilience des données et de la messagerie à instruire (CR §3 et §8). Rôle des quorums et comportement des bascules à préciser. |
| Q-010 | Quel protocole de mesure et quelles preuves conserver pour comparer les plateformes ? | Comparer des incidents pertinents avec une chronologie, l’état des billets et les interventions (CR §4–5 et §8). Protocole et preuves à définir. |

## Décisions et état des livrables

Le [registre ADR](adr/README.md) est vide. Les modèles sont disponibles. Application, infrastructures et tests restent à réaliser. Voir la [préparation du 17 novembre](coaching/2026-11-17-preparation.md) pour les arbitrages proposés.
