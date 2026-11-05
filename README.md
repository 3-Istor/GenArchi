# GenArchi — Génération Architecture

Projet pédagogique (EPITA, S9 SOAR) : **une même application web résiliente**, une billetterie, déployée sur deux générations de plateforme, puis comparée à partir de preuves observées.

| | Platform 2 « datacenter virtuel » | Platform 3 « born to be cloud » |
|---|---|---|
| Où | GCP `europe-west9`, zones a / b = DC1 / DC2, zone c = site témoin | GCP, Cloud Run dans `europe-west1` et `europe-west4` |
| Qui survit à la panne | L'infrastructure : clusters redondés (Patroni, RabbitMQ, NAS sur disque répliqué) | L'application : instances jetables, données multi-région |
| Qui agit | Un humain, avec un runbook | Le système (bascule de région, canary, rollback) |
| Livrable | [`infra/p2/`](infra/p2/) : OpenTofu + Ansible | [`infra/p3/`](infra/p3/) : OpenTofu |
| URL | `https://p2.genarchi.3istor.com` | `https://p3.genarchi.3istor.com` |

Architectures et choix : [`docs/architecture/`](docs/architecture/README.md), [ADR](docs/adr/README.md). Contrats (API, événements, exécution, plateformes) : [`contracts/`](contracts/README.md).

## Démarrer (NixOS ou Ubuntu)

Tout passe par `make`. `make help` liste les cibles.

**NixOS** (ou tout Linux/macOS avec Nix) :

```bash
nix develop          # ou `direnv allow` : OpenTofu, Python 3.13, uv, Ansible, gcloud, k6, shellcheck…
make setup
```

**Ubuntu 24.04+** :

```bash
scripts/bootstrap-ubuntu.sh   # paquets système, Docker, mise
mise install                  # mêmes versions d'outils que le flake (mise.toml)
make setup
```

`make doctor` vérifie que tout est en place.

## En local, sans compte cloud

```bash
make test               # tests de contrat (backend mémoire)
make test-integration   # mêmes tests sur PostgreSQL, Firestore (émulateur) et RabbitMQ (piles up-p2/up-p3 arrêtées)
make up-p2              # app « comme en P2 » : http://localhost:8080
make up-p3              # app « comme en P3 » : http://localhost:8090
make smoke-local        # parcours complet sur les deux piles
make p2-lab             # configuration Ansible de la P2 jouée sur des conteneurs Debian 13
make validate lint      # OpenTofu validate, ruff, shellcheck, frontière P2/P3
```

## Déployer sur GCP

Une fois pour l'équipe : `make bootstrap` (bucket d'état OpenTofu partagé). Puis, depuis le poste de chacun :

```bash
cp infra/p3/env.mk.example infra/p3/env.mk   # P3_PROJECT, TF_STATE_BUCKET
export CLOUDFLARE_API_TOKEN=…                 # DNS de 3istor.com
make p3-deploy                                # image (Cloud Build) + infra + smoke

cp infra/p2/env.mk.example infra/p2/env.mk   # P2_PROJECT, TF_STATE_BUCKET
make p2-deploy                                # infra + configuration Ansible + smoke
```

Procédures d'exploitation : [`docs/runbooks/`](docs/runbooks/README.md). Aucun déploiement, aucune destruction ni injection de panne sans l'accord de l'équipe sur l'action et la cible.

## Organisation

```text
app/                  Application (Python 3.13, FastAPI), un code, des adaptateurs par plateforme
contracts/            API OpenAPI, événements CloudEvents, contrat d'exécution, engagements P2/P3
infra/bootstrap/      Bucket d'état OpenTofu
infra/p2/             OpenTofu (VM, réseau, LB) + Ansible (rôles) + labo local
infra/p3/             OpenTofu (Cloud Run, Firestore, LB global, Eventarc…) + scripts canary
docs/architecture/    Specs et challenge P2/P3          docs/adr/       Décisions
docs/runbooks/        Exploitation                      docs/cadrage.md Consignes et questions ouvertes
scripts/              Smoke test, sonde de résilience, vérification de frontière P2/P3
tests/resilience/     Scénarios et preuves
```

Pour contribuer avec un agent : [AGENTS.md](AGENTS.md).
