# Scénarios et preuves de résilience

**Aucun test exécuté et aucune preuve disponible au démarrage.** Les critères définitifs restent à confirmer : [Q-001 et Q-010](../../docs/cadrage.md).

## Utilisation

1. Copier le [modèle de scénario](modele-scenario.md) sous `scenarios/RES-NNN-sujet.md`, à partir de `RES-001`. Créer ce dossier lors du premier scénario réel.
2. Définir avant exécution le parcours, la cible, la panne, les observations attendues, les seuils validés et la remise en état. Faire confirmer les éléments inconnus ; ne pas considérer un critère absent comme satisfait.
3. Sur une cible autorisée, copier le [modèle de preuve](modele-preuve.md) sous `preuves/AAAA-MM-JJ-p2-ou-p3-RES-NNN.md`. Créer le dossier lors du premier relevé réel.
4. Relier scénario et preuve ; conserver les observations, leur méthode de mesure et des pièces expurgées de secrets. Si le code n’a pas encore de commit, indiquer une version d’artefact identifiable ou l’impossibilité de reproduire exactement la version.

Lors de la copie d’un modèle dans un sous-dossier, adapter ses liens relatifs à sa nouvelle position et remplacer les champs à compléter avant usage.

Pour comparer P2/P3, conserver un parcours et une panne comparables, tout en précisant les différences de cible et de protocole. La perte d’une instance applicative est une proposition du [kickoff, diapositive 6](../../docs/references/originaux/kickoff.pptx), à confirmer au coaching.

Résultats possibles d’un relevé : **non exécuté**, **réussi**, **échoué**, **non concluant**. Une revue documentaire ou un déploiement réussi ne vaut pas preuve de résilience.
