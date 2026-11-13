# Préparation du coaching du mardi 17 novembre 2026

Présentation sur slides, sans démonstration en direct. Horaire, participants et porteurs à confirmer.

Le [support PowerPoint](2026-11-17-coaching-2.pptx) présente la billetterie commune et les deux plateformes développées. Les schémas s’appuient sur la branche d’implémentation au commit `e2daaf9`. Le [compte rendu du 3 novembre](2026-11-03-restitution.md) donne le contexte des arbitrages.

## Déroulé proposé

| Diapositives | Sujet | Éléments à présenter |
| --- | --- | --- |
| 1 à 3 | État et architectures | Parcours d’achat jusqu’à l’émission du QR. P2 sur VM avec bascule PostgreSQL par Patroni et vérification par l’équipe. P3 sur Cloud Run avec Firestore multirégion et émission événementielle. |
| 4 | Achat interrompu | La confirmation n’arrive pas. La même requête est rejouée avec sa clé d’idempotence et le stock et les billets sont contrôlés. Le symptôme métier est commun. La panne technique proposée diffère, avec perte du primaire PostgreSQL en P2 et perte d’accès à Firestore depuis une région en P3. |
| 5 | Début de PRA | Détection, rétablissement, vérification des ventes et restauration en cas de corruption. Les objectifs de reprise pour la panne ciblée et les responsables d’incident restent à valider. |
| 6 | Arbitrages | Frontière P2/P3, comparabilité des pannes, preuves attendues, acceptation d’OpenTofu et Ansible, échéance et format de la soutenance. |

## Preuves et prochaines vérifications

- **P2.** La branche d’implémentation documente un essai en conteneurs sous cinq achats par seconde. La perte du primaire a entraîné 43 secondes de réponses 503, avec un stock cohérent et aucun billet perdu. L’essai cloud reste à confirmer.
- **P3.** La branche documente une validation statique de l’infrastructure et des essais applicatifs sur émulateurs. Le routage de secours sur GCP reste à vérifier. Le test de mise en indisponibilité de l’API d’une région documenté dans le runbook vérifie le routage, sans simuler la perte de Firestore.
- **Comparaison.** Préparer une chronologie des achats, vérifier la conservation des commandes confirmées et l’absence de doublon après rejeu, puis relever les interventions humaines. Utiliser les [modèles de scénario et de preuve](../../tests/resilience/README.md) pour consigner les résultats d’un essai autorisé.

Reporter les réponses dans le [cadrage](../cadrage.md), notamment Q-001 à Q-005, Q-009 et Q-010. Consigner les actions avec leurs porteurs et échéances.
