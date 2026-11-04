#!/usr/bin/env bash
# Bascule manuelle du NAS (runbook docs/runbooks/p2-nas.md). Un humain décide, le script exécute.
#   1. isole l'ancien NAS (arrêt de NFS, démontage) s'il répond encore ;
#   2. attache de force le disque régional au nouveau NAS (c'est le « fencing » : l'ancien perd le disque) ;
#   3. monte le disque et démarre NFS sur le nouveau ; l'IP virtuelle suit grâce au health check ;
#   4. rappelle de reporter P2_NAS_ACTIVE dans env.mk pour qu'OpenTofu et Ansible restent alignés.
set -euo pipefail
to="${1:?usage: nas-failover.sh nas-1|nas-2}"
: "${P2_DIR:?}" "${P2_PROJECT:?}"
case "$to" in nas-1) from=nas-2 ;; nas-2) from=nas-1 ;; *) echo "cible inconnue : $to" >&2; exit 2 ;; esac
ssh_cfg="$P2_DIR/ansible/ssh_config"
on() { ssh -F "$ssh_cfg" -o ConnectTimeout=10 "$1.p2.genarchi.internal" "${@:2}"; }
zone_of() { gcloud compute instances list --project "$P2_PROJECT" --filter="name=$1" --format='value(zone.basename())'; }
region="$(gcloud compute disks list --project "$P2_PROJECT" --filter='name=nas-tickets' --format='value(region.basename())')"

echo "1/4 isolement de $from"
on "$from" 'sudo systemctl stop nfs-server; sudo umount /srv/tickets' || echo "  $from injoignable : on continue (le force-attach le prive du disque)"

echo "2/4 attachement forcé du disque à $to"
gcloud compute instances detach-disk "$from" --project "$P2_PROJECT" --zone "$(zone_of "$from")" \
  --disk nas-tickets --disk-scope regional 2>/dev/null || true
gcloud compute instances attach-disk "$to" --project "$P2_PROJECT" --zone "$(zone_of "$to")" \
  --disk nas-tickets --disk-scope regional --device-name tickets --force-attach

echo "3/4 démarrage de NFS sur $to"
on "$to" 'sudo mount /srv/tickets && sudo systemctl enable --now nfs-server && sudo exportfs -ra'

echo "4/4 vérification de l'IP virtuelle (health check toutes les 3 s)"
for _ in $(seq 1 20); do
  state="$(gcloud compute backend-services get-health p2-nas --project "$P2_PROJECT" --region "$region" --format=json \
    | jq -r --arg h "$to" '[.[].status.healthStatus[]? | select(.instance | endswith("/" + $h)) | .healthState] | first // "?"')"
  [[ "$state" == HEALTHY ]] && break
  sleep 3
done
echo "  $to : $state"
echo "Reporter P2_NAS_ACTIVE ?= $to dans infra/p2/env.mk, puis : make p2-apply (aligne l'état OpenTofu)."
