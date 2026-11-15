#!/usr/bin/env bash
# Panne sous charge sur le labo : sonde scripts/probe.py à travers rp-1, docker kill puis docker start.
#   chaos.sh <durée_sonde_s> <panne_à_s> <remise_à_s> <hôte>...   (ex. 180 20 110 app-1b db-2 mq-2)
# La sonde tourne dans le réseau p2lab : marche aussi sous Docker Desktop, qui ne route pas 10.20.0.0/16.
set -euo pipefail
cd "$(dirname "$0")/../../.."
probe_s=$1 kill_at=$2 back_at=$3
shift 3
(($# > 0 && kill_at < back_at)) || { echo "usage : $0 <durée_sonde_s> <panne_à_s> <remise_à_s> <hôte>..." >&2; exit 2; }
targets=("${@/#/p2lab-}")
token=$(jq -r .admin_token infra/p2/lab/.secrets.json)
ts() { date -u +%H:%M:%SZ; }

echo "$(ts) sonde ${probe_s} s ; panne à +${kill_at} s, remise à +${back_at} s : $*"
# Patroni roles before the fault: the outcome depends on where the primary is.
docker exec -u postgres p2lab-db-1 patronictl -c /etc/patroni/config.yml list 2>/dev/null | grep -E 'db-[12]' || true
docker run --rm --network p2lab -v "$PWD/scripts:/s:ro" --entrypoint python3 genarchi-p2lab:trixie \
  -u /s/probe.py http://10.20.0.11 "$token" --seconds "$probe_s" --rate 5 &
probe=$!
sleep "$kill_at"
echo "$(ts) panne : docker kill ${targets[*]}"
docker kill "${targets[@]}" >/dev/null
sleep $((back_at - kill_at))
echo "$(ts) remise : docker start ${targets[*]}"
docker start "${targets[@]}" >/dev/null
wait "$probe"
