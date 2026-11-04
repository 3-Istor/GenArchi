# Préparation du coaching — 3 novembre 2026

**Statut : préparation uniquement.** Date annoncée dans le kickoff ; tenue, participants et horaire à confirmer. Aucun échange ni arbitrage n’est encore consigné.

Source : [kickoff, diapositives 4–11](../references/originaux/kickoff.pptx). Le [cours 1, diapositive 5](../references/originaux/cours-1-td-1.pptx) donne le périmètre du TD. Les questions détaillées restent dans le [cadrage](../cadrage.md).

## Objectif

Obtenir les contraintes permettant de choisir l’application et de concevoir les deux architectures sans figer prématurément les technologies.

## Questions prioritaires et propositions à discuter

Toutes les propositions ci-dessous sont non validées. Porteurs : à confirmer.

| Priorité | Questions | Proposition de départ | Précision attendue |
| --- | --- | --- | --- |
| 1 | Q-001, Q-010 | Perdre une instance applicative sur chaque plateforme et observer un même parcours avant, pendant et après la panne | Scénario admissible, critères de succès, interruption tolérée, mesures et preuves attendues |
| 2 | Q-002 | P2 : VM redondées et bascule du trafic ; P3 : instances remplaçables avec reprise automatisée | Différences minimales attendues et limites des exemples proposés |
| 3 | Q-003 | Deux ensembles Terraform séparés, une application commune | Périmètre du provisionnement, de la configuration et du déploiement ; outils complémentaires admis |
| 4 | Q-004 | Comparer les environnements accessibles, dont les pistes AWS/OpenStack du kickoff | Fournisseurs et services autorisés, accès, quotas, budget et contraintes d’usage |
| 5 | Q-005 | Utiliser les jalons internes du kickoff comme base de discussion | Grille, échéances officielles, nombre et format des suivis, format de soutenance |
| 6 | Q-006, Q-007, Q-009 | Garder un parcours applicatif limité et préciser le besoin de persistance avant de choisir la stack | Latitude sur le sujet, contraintes applicatives et place de la résilience des données |

## Éléments à apporter

Le [support de présentation](2026-11-03-coaching-1.pptx) est disponible. Insérer les images des architectures P2 et P3 sur les diapositives 3 et 4, qui ne conservent que leur titre pour laisser les Tech Leads organiser leur présentation. La diapositive 2 présente notre compréhension à confirmer sous forme de deux schémas inspirés du kickoff ; la diapositive 5 regroupe les questions en une seule liste. Les notes du présentateur contiennent les références et les précisions orales.

- Les deux pistes d’architecture du [kickoff, diapositives 4–5](../references/originaux/kickoff.pptx), à annoter comme propositions. Aucun nouveau schéma détaillé n’est encore produit.
- L’inventaire des accès disponibles, des quotas et du budget : **à constituer**, sans secrets dans le dépôt.
- Les affectations PM, Tech Leads P2/P3 et appuis transverses : **à confirmer** (Q-008).
- L’état réel : documentation initiale uniquement, aucun déploiement ni test exécuté.

## Sortie attendue et suivi

Consigner les réponses avec leur niveau de confirmation dans une restitution datée, puis mettre à jour Q-001 à Q-010 et les jalons concernés. Préparer ensuite les ADR proposées pour les choix de l’équipe. Les questions non résolues restent ouvertes ; aucune architecture ne devient acceptée par défaut.
