#!/usr/bin/env bash
# Test de fumée de bout en bout, identique pour local, P2 et P3.
# Usage : scripts/smoke.sh <BASE_URL> <ADMIN_TOKEN> <STAFF_TOKEN>
# `cond && ok || ko` est sûr ici : ok ne fait qu'afficher, ko arrête le script.
# shellcheck disable=SC2015
set -euo pipefail
BASE=${1:?BASE_URL}; ADMIN=${2:?ADMIN_TOKEN}; STAFF=${3:?STAFF_TOKEN}
C=(curl -sS --max-time 10)
ok() { printf '  \033[32m✔\033[0m %s\n' "$1"; }
ko() { printf '  \033[31m✘\033[0m %s\n' "$1"; exit 1; }

echo "Smoke test sur $BASE"
v=$("${C[@]}" "$BASE/version") || ko "GET /version"
ok "version : $(jq -r '"\(.platform) · \(.instance) · contrat \(.contract_version)"' <<<"$v")"
[[ $("${C[@]}" -o /dev/null -w '%{http_code}' "$BASE/readyz") == 200 ]] && ok "readyz" || ko "readyz"

start=$(date -u -d '+30 days' +%FT%TZ 2>/dev/null || date -u -v+30d +%FT%TZ)
open=$(date -u -d '-1 minute' +%FT%TZ 2>/dev/null || date -u -v-1M +%FT%TZ)
ev=$("${C[@]}" -X POST "$BASE/events" -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d "{\"name\":\"Smoke $(date +%s)\",\"venue\":\"EPITA\",\"starts_at\":\"$start\",\"sales_open_at\":\"$open\",\"capacity\":50,\"price_cents\":1000}")
eid=$(jq -r .id <<<"$ev"); [[ $eid == evt_* ]] && ok "événement créé $eid" || ko "création d'événement : $ev"

key=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || uuidgen)
order=$("${C[@]}" -X POST "$BASE/events/$eid/orders" -H "Idempotency-Key: $key" -H 'Content-Type: application/json' \
  -d '{"buyer_email":"smoke@example.com","quantity":2}')
oid=$(jq -r .id <<<"$order"); tid=$(jq -r '.tickets[0].id' <<<"$order")
[[ $(jq '.tickets | length' <<<"$order") == 2 ]] && ok "commande $oid (2 billets)" || ko "achat : $order"
replay=$("${C[@]}" -o /dev/null -w '%{http_code}' -X POST "$BASE/events/$eid/orders" -H "Idempotency-Key: $key" \
  -H 'Content-Type: application/json' -d '{"buyer_email":"smoke@example.com","quantity":2}')
[[ $replay == 200 ]] && ok "rejeu idempotent (200)" || ko "rejeu : $replay"
[[ $("${C[@]}" "$BASE/events/$eid" | jq .remaining) == 48 ]] && ok "stock décrémenté une seule fois" || ko "stock"

t0=$(date +%s)
for _ in $(seq 1 300); do
  st=$("${C[@]}" "$BASE/tickets/$tid" | jq -r .status)
  [[ $st == issued ]] && break; sleep 1
done
[[ $st == issued ]] && ok "QR émis en $(( $(date +%s) - t0 )) s" || ko "billet toujours $st"
[[ $("${C[@]}" -L "$BASE/tickets/$tid/qr" | head -c 4 | od -An -c | tr -d ' ') == *PNG* ]] && ok "QR téléchargé (PNG)" || ko "QR"

[[ $("${C[@]}" -o /dev/null -w '%{http_code}' -X POST "$BASE/tickets/$tid/scan" -H "Authorization: Bearer $STAFF") == 200 ]] \
  && ok "premier scan accepté" || ko "scan"
[[ $("${C[@]}" -X POST "$BASE/tickets/$tid/scan" -H "Authorization: Bearer $STAFF" | jq -r .code) == already_scanned ]] \
  && ok "second scan refusé (already_scanned)" || ko "second scan"
echo "Tout est vert."
