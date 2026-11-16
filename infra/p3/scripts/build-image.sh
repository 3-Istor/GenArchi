#!/usr/bin/env bash
# Construit l'image de l'app avec Cloud Build (aucun Docker local requis) et écrit son digest dans .image.
set -euo pipefail
: "${P3_DIR:?}" "${P3_PROJECT:?}" "${P3_VERSION:?}"
root="$(git rev-parse --show-toplevel)"
registry="$(tofu -chdir="$P3_DIR" output -raw registry)"
tag="$registry/genarchi:$P3_VERSION"

# APP_VERSION is baked into the image (Dockerfile ARG): each revision reports its own version in /version.
config="$(mktemp)"
trap 'rm -f "$config"' EXIT
cat > "$config" <<'EOF'
steps:
  - name: gcr.io/cloud-builders/docker
    args: [build, --build-arg, "APP_VERSION=${_VERSION}", -t, "${_TAG}", .]
images: ["${_TAG}"]
EOF
gcloud builds submit "$root/app" --project "$P3_PROJECT" --region europe-west1 --config "$config" \
  --substitutions "_TAG=$tag,_VERSION=$P3_VERSION" --quiet
digest="$(gcloud artifacts docker images describe "$tag" --project "$P3_PROJECT" --format='value(image_summary.digest)')"
echo "$registry/genarchi@$digest" > "$P3_DIR/.image"
echo "image : $(cat "$P3_DIR/.image")"
