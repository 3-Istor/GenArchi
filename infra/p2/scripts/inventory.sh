#!/usr/bin/env bash
# Génère l'inventaire Ansible et la configuration SSH (bastion joint par IAP, comptes OS Login).
set -euo pipefail
: "${P2_DIR:?}" "${P2_PROJECT:?}"
ans="$P2_DIR/ansible"
umask 077

tofu -chdir="$P2_DIR" output -raw ansible_inventory > "$ans/inventory/generated.yml"

# Clé SSH dédiée, enregistrée sur le compte Google (OS Login) : rien n'est copié à la main sur les VM.
key="${GENARCHI_SSH_KEY:-$HOME/.ssh/genarchi_ed25519}"
[[ -f "$key" ]] || ssh-keygen -q -t ed25519 -N "" -C "genarchi-p2" -f "$key"
gcloud compute os-login ssh-keys add --project "$P2_PROJECT" --key-file "$key.pub" --ttl 30d >/dev/null
user="$(gcloud compute os-login describe-profile --project "$P2_PROJECT" --format='value(posixAccounts[0].username)')"
zone="$(tofu -chdir="$P2_DIR" output -json bastion | jq -r .zone | sed 's#.*/##')"
net="$(tofu -chdir="$P2_DIR" output -raw network_prefix)"

cat > "$ans/ssh_config" <<CFG
# Généré par infra/p2/scripts/inventory.sh
Host bastion
  HostName bastion
  User $user
  IdentityFile $key
  ProxyCommand gcloud compute start-iap-tunnel bastion 22 --listen-on-stdin --project $P2_PROJECT --zone $zone --verbosity=warning
  StrictHostKeyChecking accept-new
  UserKnownHostsFile $ans/known_hosts

Host $net.* *.p2.genarchi.internal
  User $user
  IdentityFile $key
  ProxyJump bastion
  StrictHostKeyChecking accept-new
  UserKnownHostsFile $ans/known_hosts
CFG
echo "inventaire : $ans/inventory/generated.yml ; SSH : ssh -F $ans/ssh_config <ip>"
