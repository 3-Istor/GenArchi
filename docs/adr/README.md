# Décisions d’architecture

**Aucune ADR n’est acceptée au 2 novembre 2026.** Les ADR 0001 à 0013 sont des propositions des tech leads, à valider. Les exemples du kickoff ne valent pas décision.

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
| [0001](0001-fournisseur-gcp.md) | Fournisseur cloud : Google Cloud | proposé | — | — |
| [0002](0002-p2-deux-zones-bascule-manuelle.md) | P2 : deux zones, bascule manuelle | proposé | — | — |
| [0003](0003-p3-cloud-run-services.md) | P3 : Cloud Run services plutôt que GKE ou Cloud Run functions | proposé | — | — |
| [0004](0004-p3-drp-permanent-rollback-auto.md) | P3 : test de DRP permanent et rollback automatique | proposé | — | — |
| [0005](0005-p3-firestore-eur3.md) | P3 : Firestore multi-région eur3 | proposé | — | — |
| [0006](0006-p2-equipements-reseau-manages.md) | P2 : équipements réseau managés | proposé | — | — |
| [0007](0007-app-python-fastapi.md) | Langage de l'application : Python + FastAPI | proposé | — | — |
| [0008](0008-app-billetterie.md) | Application : billetterie, un seul code, deux jeux d'adaptateurs | proposé | — | — |
| [0009](0009-p2-sauvegarde-pgdump-snapshots.md) | P2 : sauvegarde par pg_dump et snapshots de disques | proposé | — | — |
| [0010](0010-p2-build-automatise-run-manuel.md) | P2 : build automatisé, run manuel | proposé | — | — |
| [0011](0011-p3-sweeper.md) | P3 : rattrapage des publications perdues par un sweeper | proposé | — | — |
| [0012](0012-p2-supervision-zabbix.md) | P2 : supervision Zabbix | proposé | — | — |
| [0013](0013-regions.md) | Régions | proposé | — | — |

Sujets à instruire après coaching : application commune, environnements P2/P3, persistance, architecture de chaque plateforme et protocole de résilience. Cette liste ne préjuge d’aucun choix.
