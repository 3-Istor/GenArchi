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
run() { gcloud run "$@" --project "$P3_PROJECT" --quiet; }

count() { # count <revision> <filtre supplémentaire>
  gcloud logging read --project "$P3_PROJECT" --freshness="${WATCH_SECONDS}s" --format='value(timestamp)' \
    "resource.type=\"cloud_run_revision\" AND resource.labels.revision_name=\"$1\" AND httpRequest.status>0 $2" | wc -l
}

for region in "${regions[@]}"; do
  stable="$(run services describe "$svc" --region "$region" --format='value(status.traffic[0].revisionName)')"
  echo "[$region] révision stable : $stable"
  run deploy "$svc" --region "$region" --image "$image" --no-traffic --tag canary
  canary="$(run services describe "$svc" --region "$region" --format='value(status.latestCreatedRevisionName)')"
  run services update-traffic "$svc" --region "$region" --to-revisions "$canary=10,$stable=90"
  echo "[$region] $canary reçoit 10 % pendant ${WATCH_SECONDS}s"
  sleep "$WATCH_SECONDS"

  total="$(count "$canary" "")"
  errors="$(count "$canary" "AND httpRequest.status>=500")"
  echo "[$region] canary : $errors erreurs 5xx sur $total requêtes"
  if awk -v e="$errors" -v t="$total" -v m="$MAX_ERROR_RATIO" 'BEGIN { exit !(t > 0 && e / t > m) }'; then
    echo "[$region] seuil dépassé : retour à $stable" >&2
    run services update-traffic "$svc" --region "$region" --to-revisions "$stable=100"
    exit 1
  fi
  run services update-traffic "$svc" --region "$region" --to-latest
  echo "[$region] $canary promue à 100 %"
done
