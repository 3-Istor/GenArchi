# GenArchi : point d'entrée unique, identique sur NixOS (`nix develop`) et Ubuntu (`mise`).
# `make help` liste les cibles. Les cibles cloud lisent infra/<p2|p3>/env.mk (voir *.example).
SHELL := bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help
APP := app
TOFU ?= tofu

-include infra/p2/env.mk
-include infra/p3/env.mk

help: ## Affiche cette aide
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

## --- Poste de travail --------------------------------------------------------------------------
doctor: ## Vérifie que les outils sont installés
	@for t in tofu uv python3 ansible-playbook gcloud docker jq; do \
	  printf '  %-17s' $$t; command -v $$t >/dev/null && echo ok || echo "MANQUANT"; done

setup: ## Installe les dépendances Python de l'app et les collections Ansible
	cd $(APP) && uv sync --all-extras
	ansible-galaxy collection install -r infra/p2/ansible/requirements.yml >/dev/null

## --- Qualité -------------------------------------------------------------------------------------
lint: ## Lint app + OpenTofu + scripts + frontière P2/P3
	cd $(APP) && uv run ruff check . && uv run ruff format --check .
	$(TOFU) fmt -check -recursive infra
	shellcheck scripts/*.sh infra/p2/scripts/*.sh infra/p3/scripts/*.sh
	python3 scripts/check_boundary.py

test: ## Tests unitaires et de contrat (backend mémoire)
	cd $(APP) && uv run pytest -q

test-integration: services ## Tests sur PostgreSQL, Firestore (émulateur) et RabbitMQ
	cd $(APP) && TEST_DATABASE_URL=postgresql://genarchi:genarchi@localhost:55432/genarchi \
	  FIRESTORE_EMULATOR_HOST=localhost:8681 TEST_AMQP_URL=amqp://genarchi:genarchi@localhost:55672/ \
	  uv run pytest -q

validate: ## `tofu validate` des deux plateformes (sans compte GCP)
	for d in infra/bootstrap infra/p2 infra/p3; do $(TOFU) -chdir=$$d init -backend=false -input=false >/dev/null && $(TOFU) -chdir=$$d validate; done

## --- Local ---------------------------------------------------------------------------------------
services: ## Démarre PostgreSQL, RabbitMQ et l'émulateur Firestore
	docker compose --profile services up -d --wait

up-p2: ## App locale « comme en P2 » : http://localhost:8080
	docker compose --profile p2 up -d --build --wait
	@echo "  Seed : docker compose --profile p2 run --rm api-p2 seed"

up-p3: ## App locale « comme en P3 » : http://localhost:8090
	docker compose --profile p3 up -d --build --wait

down: ## Arrête tout l'environnement local
	docker compose --profile p2 --profile p3 --profile services down -v

smoke-local: ## Test de fumée sur les deux piles locales
	scripts/smoke.sh http://localhost:8080 local-admin-token local-staff-token
	scripts/smoke.sh http://localhost:8090 local-admin-token local-staff-token

## --- Platform 3 (GCP) ----------------------------------------------------------------------------
include infra/p3/p3.mk

## --- Platform 2 (GCP) ----------------------------------------------------------------------------
include infra/p2/p2.mk

.PHONY: help doctor setup lint test test-integration validate services up-p2 up-p3 down smoke-local
