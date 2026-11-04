#!/usr/bin/env bash
# Smoke test de la P3 : lit l'URL et les jetons (Secret Manager), puis lance le smoke commun.
set -euo pipefail
: "${P3_DIR:?}" "${P3_PROJECT:?}"
root="$(git rev-parse --show-toplevel)"
url="$(tofu -chdir="$P3_DIR" output -raw url)"
secret() { gcloud secrets versions access latest --project "$P3_PROJECT" --secret "$(tofu -chdir="$P3_DIR" output -raw "$1")"; }
"$root/scripts/smoke.sh" "$url" "$(secret admin_token_secret)" "$(secret staff_token_secret)"
