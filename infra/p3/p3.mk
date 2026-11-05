# Cibles cloud de la Platform 3. Variables : infra/p3/env.mk (voir env.mk.example).
P3_DIR      := infra/p3
P3_PROJECT  ?=
P3_VERSION  ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
P3_TFVARS   := -var project_id=$(P3_PROJECT)
P3_TOFU     := $(TOFU) -chdir=$(P3_DIR)

p3-check:
	@test -n "$(P3_PROJECT)" || { echo "P3_PROJECT manquant : cp infra/p3/env.mk.example infra/p3/env.mk"; exit 1; }
	@test -n "$(TF_STATE_BUCKET)" || { echo "TF_STATE_BUCKET manquant (make bootstrap)"; exit 1; }
	@test -n "$$CLOUDFLARE_API_TOKEN" || { echo "export CLOUDFLARE_API_TOKEN=... (droit DNS edit sur 3istor.com)"; exit 1; }
	@gcloud auth application-default print-access-token >/dev/null 2>&1 || { echo "gcloud auth application-default login"; exit 1; }

p3-init: p3-check ## P3 : tofu init (état dans le bucket GCS)
	$(P3_TOFU) init -input=false -backend-config="bucket=$(TF_STATE_BUCKET)"

p3-plan: p3-init ## P3 : plan
	$(P3_TOFU) plan $(P3_TFVARS) -var app_image="$$(cat $(P3_DIR)/.image 2>/dev/null)" -var app_version=$(P3_VERSION)

p3-registry: p3-init
	$(P3_TOFU) apply -input=false -auto-approve $(P3_TFVARS) \
	  -target=google_project_service.apis -target=google_artifact_registry_repository.app

p3-image: p3-registry ## P3 : construit l'image avec Cloud Build et note son digest
	P3_DIR=$(P3_DIR) P3_PROJECT=$(P3_PROJECT) P3_VERSION=$(P3_VERSION) $(P3_DIR)/scripts/build-image.sh

p3-apply: p3-init ## P3 : applique l'infra avec l'image notée par p3-image
	@test -s $(P3_DIR)/.image || { echo "pas d'image : make p3-image"; exit 1; }
	$(P3_TOFU) apply -input=false $(P3_TFVARS) -var app_image="$$(cat $(P3_DIR)/.image)" -var app_version=$(P3_VERSION)

p3-deploy: p3-image p3-apply p3-smoke ## P3 : premier déploiement complet (image + infra + smoke)

p3-smoke: ## P3 : test de fumée contre l'URL publique
	P3_DIR=$(P3_DIR) P3_PROJECT=$(P3_PROJECT) $(P3_DIR)/scripts/smoke.sh

p3-canary: p3-image ## P3 : nouvelle version en canary 10 % → 100 %, rollback si erreurs
	P3_DIR=$(P3_DIR) P3_PROJECT=$(P3_PROJECT) $(P3_DIR)/scripts/canary.sh "$$(cat $(P3_DIR)/.image)"
	$(P3_TOFU) apply -input=false -auto-approve $(P3_TFVARS) -var app_image="$$(cat $(P3_DIR)/.image)" -var app_version=$(P3_VERSION)

p3-chaos-region: ## P3 : lance tout de suite le test de panne de région (10 min)
	gcloud run jobs execute p3-chaos-region --project $(P3_PROJECT) --region $$($(P3_TOFU) output -json regions | jq -r '.[0]')

p3-destroy: p3-init ## P3 : détruit l'infra (Firestore est conservé : deletion protection)
	$(P3_TOFU) destroy $(P3_TFVARS) -var app_image="$$(cat $(P3_DIR)/.image 2>/dev/null)"

.PHONY: p3-check p3-init p3-plan p3-registry p3-image p3-apply p3-deploy p3-smoke p3-canary p3-chaos-region p3-destroy
