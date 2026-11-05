# Cibles cloud de la Platform 2. Variables : infra/p2/env.mk (voir env.mk.example).
# Build automatisé (OpenTofu + Ansible), exploitation manuelle par runbooks (docs/runbooks/p2-*.md).
P2_DIR        := infra/p2
P2_PROJECT    ?=
P2_NAS_ACTIVE ?= nas-1
P2_TFVARS     := -var project_id=$(P2_PROJECT) -var nas_active=$(P2_NAS_ACTIVE)
P2_TOFU       := $(TOFU) -chdir=$(P2_DIR)
P2_ANSIBLE    := cd $(P2_DIR)/ansible && ANSIBLE_CONFIG=ansible.cfg ansible-playbook
P2_SSH        := ssh -F $(P2_DIR)/ansible/ssh_config

p2-check:
	@test -n "$(P2_PROJECT)" || { echo "P2_PROJECT manquant : cp infra/p2/env.mk.example infra/p2/env.mk"; exit 1; }
	@test -n "$(TF_STATE_BUCKET)" || { echo "TF_STATE_BUCKET manquant (make bootstrap)"; exit 1; }
	@test -n "$$CLOUDFLARE_API_TOKEN" || { echo "export CLOUDFLARE_API_TOKEN=... (droit DNS edit sur 3istor.com)"; exit 1; }
	@gcloud auth application-default print-access-token >/dev/null 2>&1 || { echo "gcloud auth application-default login"; exit 1; }

p2-init: p2-check ## P2 : tofu init (état dans le bucket GCS)
	$(P2_TOFU) init -input=false -backend-config="bucket=$(TF_STATE_BUCKET)"

p2-plan: p2-init ## P2 : plan
	$(P2_TOFU) plan $(P2_TFVARS)

p2-apply: p2-init ## P2 : crée ou met à jour les VM, le réseau et les load balancers
	$(P2_TOFU) apply -input=false $(P2_TFVARS)

p2-inventory: ## P2 : génère l'inventaire Ansible et la config SSH (bastion via IAP)
	P2_DIR=$(P2_DIR) P2_PROJECT=$(P2_PROJECT) $(P2_DIR)/scripts/inventory.sh

p2-configure: p2-inventory ## P2 : installe et configure tous les serveurs (Ansible, idempotent)
	$(P2_ANSIBLE) site.yml -e discord_webhook="$${P2_DISCORD_WEBHOOK:-}"

p2-release: p2-inventory ## P2 : déploie la version courante de l'app, serveur par serveur
	$(P2_ANSIBLE) app.yml

p2-deploy: p2-apply p2-configure p2-smoke ## P2 : premier déploiement complet (infra + config + smoke)

p2-smoke: ## P2 : test de fumée contre l'URL publique
	@inv=$(P2_DIR)/ansible/inventory/generated.yml; \
	  tok() { python3 -c "import sys,yaml; print(yaml.safe_load(open('$$inv'))['all']['vars']['secrets']['$$1'])"; }; \
	  scripts/smoke.sh "$$($(P2_TOFU) output -raw url)" "$$(tok admin_token)" "$$(tok staff_token)"

p2-ssh: ## P2 : shell sur un serveur (HOST=db-1)
	$(P2_SSH) $${HOST:?HOST=nom}.p2.genarchi.internal

p2-ui: ## P2 : tunnels vers Zabbix (localhost:8081/zabbix) et RabbitMQ (localhost:15672)
	@echo "Zabbix : http://localhost:8081/zabbix   RabbitMQ : http://localhost:15672   (Ctrl-C pour fermer)"
	$(P2_SSH) -N -L 8081:monitoring.p2.genarchi.internal:80 -L 15672:mq-1.p2.genarchi.internal:15672 bastion

## --- Runbooks P2 (docs/runbooks/) ----------------------------------------------------------------
p2-db-status: ## Runbook : état du cluster PostgreSQL (Patroni)
	$(P2_SSH) db-1.p2.genarchi.internal sudo -u postgres patronictl -c /etc/patroni/config.yml list

p2-db-switchover: ## Runbook : bascule planifiée du primaire vers l'autre DC (CANDIDATE=db-2)
	$(P2_SSH) db-1.p2.genarchi.internal sudo -u postgres patronictl -c /etc/patroni/config.yml switchover --candidate $${CANDIDATE:?CANDIDATE=db-1|db-2} --force

p2-nas-failover: ## Runbook : bascule du NAS (TO=nas-2) ; voir docs/runbooks/p2-nas.md
	P2_DIR=$(P2_DIR) P2_PROJECT=$(P2_PROJECT) $(P2_DIR)/scripts/nas-failover.sh $${TO:?TO=nas-1|nas-2}

p2-backup-status: ## Runbook : état des sauvegardes Barman
	$(P2_SSH) backup.p2.genarchi.internal sudo -u barman barman list-backups genarchi

p2-destroy: p2-init ## P2 : détruit toute la P2
	$(P2_TOFU) destroy $(P2_TFVARS)

.PHONY: p2-check p2-init p2-plan p2-apply p2-inventory p2-configure p2-release p2-deploy p2-smoke p2-ssh p2-ui \
	p2-db-status p2-db-switchover p2-nas-failover p2-backup-status p2-destroy

## --- Labo local (conteneurs, sans GCP) -------------------------------------------------------------
p2-lab: ## Labo : joue la configuration Ansible de la P2 sur des conteneurs Debian 13
	python3 $(P2_DIR)/lab/lab.py up
	python3 $(P2_DIR)/lab/lab.py inventory >/dev/null
	cd $(P2_DIR)/ansible && ANSIBLE_CONFIG=ansible.cfg ansible-playbook -i ../lab/inventory.json ../lab/lab.yml

p2-lab-smoke: ## Labo : test de fumée à travers le reverse proxy
	@s=$(P2_DIR)/lab/.secrets.json; scripts/smoke.sh http://10.20.0.11 "$$(jq -r .admin_token $$s)" "$$(jq -r .staff_token $$s)"

p2-lab-down: ## Labo : supprime les conteneurs
	python3 $(P2_DIR)/lab/lab.py down

.PHONY: p2-lab p2-lab-smoke p2-lab-down
