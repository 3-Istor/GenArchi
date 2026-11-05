# P2 — Déployer, mettre en production, patcher

## Prérequis (une fois par poste)

1. Outils : `nix develop` (NixOS) ou `scripts/bootstrap-ubuntu.sh` puis `mise install` (Ubuntu). `make doctor` doit être vert.
2. `gcloud auth login` puis `gcloud auth application-default login`.
3. Rôles IAM sur le projet P2 : `roles/compute.osAdminLogin` (SSH par OS Login), `roles/iap.tunnelResourceAccessor` (bastion), et les droits d'écriture OpenTofu (`roles/editor` en TD).
4. `cp infra/p2/env.mk.example infra/p2/env.mk`, remplir `P2_PROJECT` et `TF_STATE_BUCKET`.
5. `export CLOUDFLARE_API_TOKEN=…` (jeton « DNS edit » sur `3istor.com`, demandé au propriétaire de la zone).

## Premier déploiement

```bash
make bootstrap        # une seule fois pour toute l'équipe : bucket d'état partagé
make p2-deploy        # = p2-apply (≈ 5 min) + p2-configure (≈ 20 min) + p2-smoke
```

Le certificat TLS est émis après la création du CNAME d'autorisation (quelques minutes) ; avant, `p2-smoke` échoue en TLS : relancer `make p2-smoke`.

## Mettre une version en production

1. RFC : version (tag git), fenêtre, risque, retour arrière. Validée par l'équipe.
2. `git checkout <tag>` puis `make p2-release`. Ansible construit la wheel, migre le schéma (une fois), puis met à jour les serveurs d'application **un par un** ; chacun doit répondre `/readyz` avant de passer au suivant.
3. Vérifier : `make p2-smoke`, tableau de bord Zabbix (`make p2-ui`).
4. Retour arrière : `git checkout <tag précédent>` puis `make p2-release`. Les trois dernières versions restent installées sur les serveurs (`/opt/genarchi/venv-*`).

Une migration de schéma doit rester compatible avec la version précédente (ajout de colonne, pas de suppression) pour que le retour arrière reste possible.

## Patcher les serveurs (mensuel)

Un serveur à la fois, en commençant par le DC2, jamais deux serveurs du même cluster en même temps :

```bash
make p2-ssh HOST=app-1b   # puis : sudo apt update && sudo apt upgrade && sudo reboot
```

- Serveurs d'app et reverse proxies : sortis de la rotation automatiquement pendant le redémarrage.
- Base : patcher d'abord le réplica, puis `make p2-db-switchover CANDIDATE=<réplica>`, puis patcher l'ancien primaire.
- RabbitMQ, etcd : un nœud à la fois, attendre que le cluster soit revenu à 3 membres.
- `make p2-configure` après le patch réaligne la configuration (idempotent).

## Tester la configuration sans GCP

`make p2-lab` joue tout le `site.yml` sur des conteneurs Debian 13 + systemd (cluster Patroni, RabbitMQ, Zabbix, Apache, app), puis `make p2-lab-smoke`. Voir `infra/p2/lab/lab.py` pour ce que le labo ne reproduit pas.
