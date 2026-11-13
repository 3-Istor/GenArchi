# Décisions d’architecture

**Aucune ADR technique n’est enregistrée.** Le [premier coaching](../coaching/2026-11-03-restitution.md) retient la billetterie comme cas d’étude. Les architectures présentées restent des propositions.

## Créer et faire évoluer une ADR

1. Copier le [modèle](modele.md) sous `NNNN-sujet.md`, en prenant le prochain numéro libre sur quatre chiffres, à partir de `0001`. Le modèle ne réserve aucun numéro.
2. Décrire le contexte, les options réelles, la proposition et ses conséquences. Relier les questions Q-xxx du [cadrage](../cadrage.md) et les sources utiles.
3. Ajouter l’ADR à l’index ci-dessous au statut **proposé**.
4. Après validation explicite de l’équipe, indiquer les validateurs, la date et le lien vers le CR ou la restitution. Passer alors au statut **accepté**, ou **rejeté** si l’option n’est pas retenue.
5. Pour remplacer une décision acceptée, créer une nouvelle ADR. Lorsque la nouvelle est acceptée, passer l’ancienne au statut **remplacé** et relier les deux documents sans effacer la justification initiale.

Statuts autorisés : **proposé**, **accepté**, **rejeté**, **remplacé**. Le statut décrit la décision, pas l’avancement de son implémentation.

## Index

| Numéro | Sujet | Statut | Date de validation | Preuve de validation |
| --- | --- | --- | --- | --- |

Sujets à instruire après coaching : périmètre de la billetterie commune, environnements P2/P3, persistance, architecture de chaque plateforme et protocole de résilience. Cette liste ne préjuge d’aucun choix.
