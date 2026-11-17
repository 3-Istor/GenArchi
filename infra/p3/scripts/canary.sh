#!/usr/bin/env bash
# Mise en production progressive de l'API P3, région par région :
#   1. nouvelle révision sans trafic ; 2. 10 % du trafic ; 3. observation ; 4. 100 % ou retour arrière.
# Le retour arrière est automatique : aucun humain n'a à décider (critère P3).
set -euo pipefail
image="${1:?usage: canary.sh <image@digest>}"
: "${P3_DIR:?}" "${P3_PROJECT:?}"
svc="$(tofu -chdir="$P3_DIR" output -raw api_service)"
mapfile -t regions < <(tofu -chdir="$P3_DIR" output -json regions | jq -r '.[]')
WATCH_SECONDS="${WATCH_SECONDS:-300}"
MAX_ERROR_RATIO="${MAX_ERROR_RATIO:-0.02}"  # contrat P3 : rollback au-delà de 2 % de 5xx
MIN_REQUESTS="${MIN_REQUESTS:-30}"         # sans assez de trafic sur la canary, pas de promotion
((MIN_REQUESTS >= 1)) || { echo "MIN_REQUESTS doit valoir au moins 1" >&2; exit 2; }
run() { gcloud run "$@" --project "$P3_PROJECT" --quiet; }
root="$(git rev-parse --show-toplevel)"
url="$(tofu -chdir="$P3_DIR" output -raw url)"
token="$(gcloud secrets versions access latest --project "$P3_PROJECT" \
  --secret "$(tofu -chdir="$P3_DIR" output -raw admin_token_secret)")"

count() { # count <revision> <filtre supplémentaire>
  gcloud logging read --project "$P3_PROJECT" --freshness="$((WATCH_SECONDS + 120))s" --format='value(timestamp)' \
    "resource.type=\"cloud_run_revision\" AND resource.labels.revision_name=\"$1\" AND httpRequest.status>0 $2" | wc -l
}

for region in "${regions[@]}"; do
  stable="$(run services describe "$svc" --region "$region" --format='value(status.traffic[0].revisionName)')"
  echo "[$region] révision stable : $stable"
  run deploy "$svc" --region "$region" --image "$image" --no-traffic --tag canary
  canary="$(run services describe "$svc" --region "$region" --format='value(status.latestCreatedRevisionName)')"
  run services update-traffic "$svc" --region "$region" --to-revisions "$canary=10,$stable=90"
  rollback() { echo "[$region] $1 : retour à $stable" >&2; run services update-traffic "$svc" --region "$region" --to-revisions "$stable=100"; exit 1; }
  # Any failure or interruption while the canary holds 10 % sends the traffic back to the stable revision.
  trap 'rollback "interrompue"' ERR INT TERM
  # Our own traffic, pinned to this region through the LB (and the WAF): the canary gets ~10 % of it.
  echo "[$region] $canary reçoit 10 % pendant ${WATCH_SECONDS}s, sonde à 5 achats/s sur cette région"
  python3 "$root/scripts/probe.py" "$url" "$token" --seconds "$WATCH_SECONDS" --rate 5 \
    --header "X-GenArchi-Region: $region" || rollback "sonde en échec"

  total="$(count "$canary" "")"
  errors="$(count "$canary" "AND httpRequest.status>=500")"
  echo "[$region] canary : $errors erreurs 5xx sur $total requêtes"
  ((total >= MIN_REQUESTS)) || rollback "moins de $MIN_REQUESTS requêtes sur la canary"
  if awk -v e="$errors" -v t="$total" -v m="$MAX_ERROR_RATIO" 'BEGIN { exit !(e / t > m) }'; then
    rollback "seuil de 5xx dépassé"
  fi
  trap - ERR INT TERM
  run services update-traffic "$svc" --region "$region" --to-latest
  echo "[$region] $canary promue à 100 %"
done
