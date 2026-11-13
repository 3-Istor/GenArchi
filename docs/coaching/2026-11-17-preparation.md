# Préparation du coaching du mardi 17 novembre 2026

Proposition de préparation. Horaire, participants et porteurs à confirmer. Le [compte rendu du 3 novembre](2026-11-03-restitution.md) et les [diapositives présentées](2026-11-03-coaching-1.pptx) servent de point de départ. La billetterie commune est retenue pour l’étude. Les architectures et les objectifs chiffrés restent à confirmer.

## Éléments à préparer avant mardi

1. **Définir le parcours de démonstration (Q-006, Q-007).** Proposer un achat qui décrémente le stock et confirme un billet. Délimiter ce qui doit fonctionner dès le MVP pour la génération du QR code et le scan unique, présentés en diapositive 2. Fixer les règles à vérifier après une panne, dont la conservation des achats confirmés et l’absence de doublon à la relance.
2. **Annoter les deux schémas (Q-002, Q-003, Q-004, Q-009).** Reprendre les diapositives 3 et 4 et suivre le trajet d’un achat jusqu’à sa persistance. En P2, distinguer les quorums de la base et de la messagerie, la bascule prévue et la remise en état manuelle. En P3, vérifier la portée géographique et les dépendances de chaque service envisagé, notamment pour la base et les événements. Pour les deux plateformes, préciser ce que Terraform doit provisionner et ce qui dépend d’outils ou de procédures complémentaires. Relever les accès, crédits et quotas à vérifier.
3. **Préparer une fiche de panne de base commune (Q-001, Q-009, Q-010).** Partir d’un achat confirmé et suivre les requêtes avant, pendant et après la panne, dont une tentative d’achat pendant l’interruption et sa relance. Comparer le temps de reprise observé, les billets et le stock avant/après, les doublons et les interventions manuelles. Proposer des objectifs RTO/RPO justifiés par l’ouverture des ventes ou la proximité de l’événement. Préciser le mode de panne comparable et réalisable sur chaque cible. Si la panne de base s’avère difficile à reproduire, proposer la perte d’une instance applicative comme scénario de repli et expliciter le périmètre couvert. S’appuyer sur les [modèles de scénario et de preuve](../../tests/resilience/README.md).

## Arbitrages à obtenir pendant le coaching

| Questions | Arbitrage recherché |
| --- | --- |
| Q-002, Q-003 | L’usage d’une bascule automatique de la base et d’un répartiteur managé est-il compatible avec la P2 proposée ? Quel périmètre doit couvrir chacun des deux livrables Terraform ? |
| Q-001, Q-009, Q-010 | Une panne ciblée de la couche de données avec les mêmes opérations métier est-elle adaptée à la comparaison ? Quelles observations présenter en soutenance ? |
| Q-005 | Que désigne exactement le 12 janvier et en quelle année ? Quel créneau, quels critères et quel format de démonstration sont attendus ? |

## Sortie attendue

Consigner le scénario prioritaire, les limites et questions encore ouvertes, les choix confirmés et les prochaines actions avec leurs porteurs et leurs échéances. Reporter les réponses dans le [cadrage](../cadrage.md) et tracer les choix de l’équipe dans le [registre des ADR](../adr/README.md). Les fiches préparées décrivent les observations à recueillir lors de futurs essais.
