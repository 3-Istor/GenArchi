# Architecture

> Propositions des tech leads, **non validées** (ADR au statut proposé). Instantané du cadrage du 1er novembre : [`2026-11-01-dossier-cadrage.html`](2026-11-01-dossier-cadrage.html) (certains points y sont dépassés : le chaos et le rollback automatique y figurent en bonus, ils sont proposés obligatoires en P3 dans [`challenge.md`](challenge.md)).

Ordre de travail proposé :

1. **Specs texte** (ce dossier) : inventaire des composants, connexions, flux et modes de défaillance, avec des IDs stables.
2. **Challenge** ([`challenge.md`](challenge.md)) : P2 vs P2.5, P3 vs Cloud-Ready, serverless vs Kubernetes. Décisions consignées dans [`docs/adr/`](../adr/).
3. **Validation** par les deux tech leads → ADR passées au statut **accepté** avec validateurs et lien vers le CR, selon le [registre](../adr/README.md) ; contrats en `1.0.0`.
4. **Schémas Noodle** générés à partir des specs : `architecture/p2/` et `architecture/p3/` (`model.yaml`, `views/`, `layouts/`), rendus dans `architecture/diagrams/`.

| Document | Contenu |
|---|---|
| [`platform2.md`](platform2.md) | Spec P2 « datacenter virtuel » |
| [`platform3.md`](platform3.md) | Spec P3 « born to be cloud » |
| [`challenge.md`](challenge.md) | Revue de la frontière entre générations et du choix serverless |

## La même app, deux générations

| | P2 | P3 |
|---|---|---|
| Qui survit à la panne ? | L'infrastructure (redondance) | L'application (résilience) |
| Qui agit quand ça casse ? | Un humain, avec un runbook | Le système, tout seul |
| Unité | Le serveur nommé (« pet ») | Le service, instances anonymes (« cattle ») |
| Données | PostgreSQL dans une VM | Firestore multi-région |
| Fichiers | Bloc + NFS | Objet |
| Traitement asynchrone | Batch toutes les 15 min | Événements Pub/Sub |
| Mise en prod | RFC + runbook | Merge → canary → rollback auto |

## Conventions pour Noodle

- IDs préfixés `p2-` / `p3-`, en anglais, jamais renommés pour raison cosmétique.
- Sens des flèches : de celui qui ouvre la connexion vers celui qui écoute.
- Étapes numérotées = chemin de la requête ; lettres = arrière-plan.
- Les flux interdits sont listés dans chaque spec (`denied: true` + `enforced_by`).
