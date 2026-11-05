# ADR 0001 — Fournisseur cloud : Google Cloud

- Statut : accepté
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-004](../cadrage.md#registre-des-questions-ouvertes)
- Validation : acceptée au coaching 1 du 2026-11-03 (professeur), information rapportée par Brian Perret le 2026-11-04 ; restitution écrite à rédiger
- Remplace / remplacée par : sans objet

## Contexte

Plus de cluster on-prem disponible. Le kickoff cite AWS et OpenStack comme pistes ([kickoff, diapositive 5](../references/originaux/kickoff.pptx)) ; les tech leads proposent GCP. **Contradiction à arbitrer** : la question Q-004 reste ouverte et l'acceptation du fournisseur par le professeur est à confirmer au coaching.

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Google Cloud | Multi-région serverless natif (Cloud Run + LB global), Firestore multi-région, crédits d'essai possibles | Équipe à former ; exemples du cours en AWS | P2 : VM + LB régional. P3 : Cloud Run, Firestore, Pub/Sub |
| AWS | Exemples du cours (EC2, ASG, RDS, Lambda) | Écarté par l'équipe selon les tech leads, motif à documenter | Équivalents complets |
| OpenStack | Proche d'un DC privé, très P2 | Pas de cluster disponible ; services P3 limités | Bon en P2, faible en P3 |

## Décision proposée

Proposer GCP pour les deux plateformes, dans deux projets séparés.

Accepté au coaching du 3 novembre (voir l'en-tête).

## Conséquences

Tous les contrats et specs v0.1 supposent GCP (noms de services dans `contracts/platforms/` et `docs/architecture/`). Un autre fournisseur imposerait de reprendre les specs d'infra, pas les contrats d'API, de domaine et d'événements.

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
