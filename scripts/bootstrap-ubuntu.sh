#!/usr/bin/env bash
# Prépare un poste Ubuntu 24.04+ (ou Debian 12+) pour GenArchi, sans droits root au-delà d'apt.
# Sur NixOS : inutile, faire `nix develop` (ou `direnv allow`).
set -euo pipefail

if ! command -v apt-get >/dev/null; then
  echo "Ce script vise Ubuntu/Debian. Ailleurs, installer mise (https://mise.jdx.dev) puis lancer 'mise install'." >&2
  exit 1
fi

echo "==> Paquets système (curl, git, make, docker)"
sudo apt-get update -qq
sudo apt-get install -y -qq curl git make ca-certificates unzip
if ! command -v docker >/dev/null; then
  sudo apt-get install -y -qq docker.io docker-compose-v2
  sudo usermod -aG docker "$USER"
  echo "   Docker installé : se déconnecter puis se reconnecter pour l'utiliser sans sudo."
fi

echo "==> mise (gestionnaire de versions)"
if ! command -v mise >/dev/null; then
  curl -fsSL https://mise.run | sh
  export PATH="$HOME/.local/bin:$PATH"
else
  # mise 2025.8 picks the free-threaded Python build, which fails to install.
  mise self-update --yes || echo "   Mise à jour de mise impossible : la faire via son gestionnaire (voir min_version dans mise.toml)." >&2
fi

echo "==> Outils du projet (versions figées dans mise.toml)"
cd "$(dirname "$0")/.."
mise trust --yes mise.toml
mise install

cat <<'MSG'

Terminé. Ajouter à ~/.bashrc si ce n'est pas déjà fait :
  eval "$(~/.local/bin/mise activate bash)"
Puis, dans le dépôt :  make setup && make help
MSG
