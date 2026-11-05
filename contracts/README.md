# Contrats GenArchi

> **Statut : proposition v0.1, non validée.** À valider par les deux tech leads avant que le dev de l'app et la prépa des tests démarrent dessus.
> Ces contrats reposent sur des ADR au statut **proposé** ([registre](../docs/adr/README.md)), dont le fournisseur GCP ([ADR 0001](../docs/adr/0001-fournisseur-gcp.md), question Q-004 encore ouverte). Les seuils chiffrés (RTO, RPO, SLO, délais) sont des **cibles proposées** en attendant la réponse à Q-001.

Les contrats sont la **source de vérité** entre les trois chantiers du projet :

| Chantier | Consomme | Produit |
|---|---|---|
| Dev de l'app | `api/`, `events/`, `domain/`, `runtime/` | Le code qui respecte ces contrats |
| Infra Platform 2 / Platform 3 | `runtime/`, `platforms/` | Les deux Terraform (livrables) |
| Tests | tout, surtout `tests/` | Les scénarios k6, chaos et contrats |

Règle d'or : **la même application tourne sur les deux plateformes**. Seuls changent la configuration (variables d'environnement) et les adaptateurs branchés derrière les interfaces décrites dans `runtime/`.

## Contenu

| Fichier | Ce qu'il fixe |
|---|---|
| [`domain/model.md`](domain/model.md) | Entités, états, invariants métier (pas de survente, scan idempotent…) |
| [`api/openapi.yaml`](api/openapi.yaml) | API HTTP exposée aux utilisateurs, au staff et aux tests (OpenAPI 3.1) |
| [`events/`](events/) | Événements métier au format CloudEvents 1.0 + schémas JSON |
| [`runtime/app-runtime.md`](runtime/app-runtime.md) | Ce que l'app doit faire pour tourner partout (12 facteurs) et ce que chaque plateforme lui fournit |
| [`runtime/env.p2.example`](runtime/env.p2.example), [`runtime/env.p3.example`](runtime/env.p3.example), [`runtime/env.local.example`](runtime/env.local.example) | Configuration concrète par cible |
| [`platforms/platform2.md`](platforms/platform2.md) | Ce que la Platform 2 garantit, ses contraintes et son interface Terraform |
| [`platforms/platform3.md`](platforms/platform3.md) | Idem pour la Platform 3 |
| [`platforms/boundary.toml`](platforms/boundary.toml) | La frontière P2/P3 en machine : ressources Terraform interdites par plateforme, vérifiées en CI par `scripts/check_boundary.py` |
| [`tests/acceptance.md`](tests/acceptance.md) | Critères d'acceptation : tests fonctionnels de contrat + protocole T1–T8 |

## Versionnement

- Version globale dans ce fichier. `0.x` = brouillon modifiable librement par les tech leads.
- À partir de `1.0` (contrats validés) : toute modification passe par une PR qui
  1. incrémente la version (`1.1` ajout compatible, `2.0` rupture),
  2. est approuvée par **les deux** tech leads (voir `CODEOWNERS`),
  3. mentionne l'impact sur l'app, les tests et chaque plateforme.
- L'app expose la version de contrat qu'elle implémente dans `GET /version` (`contract_version`).

## Version courante

`contract_version: 0.2.0`

## Points ouverts (à trancher avant la 1.0)

0. **Fournisseur** : GCP proposé ([ADR 0001](../docs/adr/0001-fournisseur-gcp.md)) alors que le kickoff cite AWS et OpenStack (Q-004). Les contrats d'API, de domaine, d'événements et d'exécution ne dépendent pas du fournisseur ; les contrats de plateforme et les specs d'infra, si.
1. **Nom de domaine** : sans domaine, pas de certificat TLS managé. Options : un domaine pas cher, ou HTTP seul sur l'IP pour la P2 et un certificat sur la P3 uniquement.
2. **Langage de l'app** : contrat écrit pour être indépendant du langage ; packaging proposé en Python (voir [ADR 0007](../docs/adr/0007-app-python-fastapi.md)).
3. **Auth** : tokens statiques `ADMIN_TOKEN` / `STAFF_TOKEN` (suffisant pour le TD). Une vraie auth (OIDC) est hors périmètre.
4. Décisions d'architecture encore au statut « Proposé » : voir [`docs/adr/`](../docs/adr/).
