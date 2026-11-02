# ADR 0007 — Langage de l'application : Python + FastAPI

- Statut : proposé
- Date de proposition : 2026-11-02
- Auteur(s) : tech leads (noms à confirmer, Q-008)
- Questions concernées : [Q-007](../cadrage.md#registre-des-questions-ouvertes)
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

L'app doit tourner sans container en P2 (virtualenv + systemd) et en container en P3.

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| Python + FastAPI | Rapide à écrire, SDK GCP | Démarrage plus lent que Go | P2 et P3 |
| Node.js / TypeScript | Idem | — | P2 et P3 |
| Java Spring Boot | Très « serveur d'application » en P2 | Démarrage à froid lent en P3 | P2 et P3 |

## Décision proposée

Python 3.11+, FastAPI, packagé en wheel (P2) et en image (P3).

Ce choix n'est pas accepté tant que l'équipe ne l'a pas validé explicitement.

## Conséquences

À confirmer par la personne qui développe l'app. Les contrats restent indépendants du langage.

## Validation et suivi

Critères de mise en œuvre : voir [`contracts/`](../../contracts/README.md) et [`docs/architecture/`](../architecture/README.md). Preuves d'exécution : à produire.

## Références

[Challenge P2/P3](../architecture/challenge.md), [cadrage](../cadrage.md).
