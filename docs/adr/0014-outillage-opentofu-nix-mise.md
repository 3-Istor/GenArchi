# ADR 0014 — Outillage : OpenTofu, Ansible, Nix et mise

- Statut : proposé
- Date de proposition : 2026-11-04
- Auteur(s) : Brian Perret (tech lead), avec l'assistant IA
- Questions concernées : périmètre Terraform ([cadrage](../cadrage.md))
- Validation : à confirmer (date, validateurs et lien vers CR/restitution)
- Remplace / remplacée par : sans objet

## Contexte

Les deux livrables sont « Terraform ». L'équipe travaille depuis des postes NixOS et Ubuntu et lance les déploiements depuis ses PC. Terraform est sous licence BUSL depuis 1.6 (paquet non libre dans nixpkgs).

## Options étudiées

| Option | Avantages | Limites et coûts | Compatibilité avec P2/P3 |
| --- | --- | --- | --- |
| OpenTofu ≥ 1.11 | Même langage HCL et mêmes providers que Terraform, licence MPL, empaqueté partout | Quelques fonctions récentes de Terraform absentes | Totale |
| Terraform 1.x | Référence du cours | Licence BUSL, `allowUnfree` sous Nix | Totale |
| Configuration P2 par `startup-script` | Rien à installer | Pas de reprise, pas d'idempotence, secrets dans les métadonnées | Pauvre en P2 |
| Configuration P2 par Ansible | Idempotent, lisible, standard du « run » P2 | Un outil de plus | Bonne en P2, inutile en P3 |

Postes : `flake.nix` (NixOS), `mise.toml` (Ubuntu, mêmes versions), `Makefile` commun.

## Décision proposée

OpenTofu pour les deux livrables (le code reste du HCL compatible Terraform), état dans un bucket GCS versionné (`make bootstrap`), fichiers `.terraform.lock.hcl` versionnés. Ansible pour configurer la P2. `nix develop` ou `mise install` donnent les mêmes versions ; `make` est le seul point d'entrée.

## Conséquences

- Le jury peut lire le code comme du Terraform ; `terraform` fonctionne aussi sur ces fichiers (non testé).
- L'état contient les secrets générés : bucket à accès restreint à l'équipe.

## Validation et suivi

`make doctor` vert sur un poste NixOS et un poste Ubuntu ; `make validate` sans erreur.

## Références

[`flake.nix`](../../flake.nix), [`mise.toml`](../../mise.toml), [`Makefile`](../../Makefile), [`infra/bootstrap/`](../../infra/bootstrap/main.tf).
