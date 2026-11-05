# ADR 0003 — P3 : Cloud Run services plutôt que GKE ou Cloud Run functions

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-002](../cadrage.md#registre-des-questions-ouvertes), [Q-007](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

Le [cours 4, diapositive 5](../references/originaux/cours-4-p3-architecture-production.pptx) classe « Lambda / Container » en P3. Le kickoff n'impose pas d'orchestrateur ([diapositive 5](../references/originaux/kickoff.pptx)).

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Cloud Run services | Une image, multi-région natif, rien à opérer | min_instances ≥ 1 par région (service health), démarrages à froid | P3 |
| Cloud Run functions (≈ Lambda) | Très simple | Une fonction par point d'entrée : nano-services, modèle propriétaire | P3 |
| GKE Autopilot | Montre l'orchestration Kubernetes, portable | Cluster à opérer, 2 clusters pour le multi-région, coût et temps | P3 |

## Décision proposée

Cloud Run services pour `api`, `worker` et le job `sweeper`, à partir d'une seule image.

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

Comparaison et limites du serverless : [challenge §4–5](../architecture/challenge.md).

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
