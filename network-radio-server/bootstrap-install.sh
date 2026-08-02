#!/usr/bin/env bash

set -euo pipefail

REF="${REF:-main}"
TMPDIR="$(mktemp -d)"
REPO_URL="https://github.com/AF4H/AF4H.git"
SPARSE_PATH="network-radio-server"

trap 'rm -rf "$TMPDIR"' EXIT

source /etc/os-release

preflight() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "bootstrap must be run as root (use sudo)" >&2
    exit 1
  fi
  command -v apt-get >/dev/null 2>&1 || {
    echo "bootstrap requires apt-get on Debian/Ubuntu hosts" >&2
    exit 1
  }
}

install_bootstrap_tools() {
  case "${ID:-}" in
    debian|ubuntu)
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y git python3 ca-certificates curl
      ;;
    *)
      echo "unsupported distro for bootstrap: ${ID:-unknown}" >&2
      exit 1
      ;;
  esac
}

preflight
echo "Bootstrapping AF4H/network-radio-server"
install_bootstrap_tools

echo "Cloning sparse network-radio-server tree"
git clone --filter=blob:none --sparse "$REPO_URL" "$TMPDIR/AF4H"
cd "$TMPDIR/AF4H"
git sparse-checkout set "$SPARSE_PATH"
git checkout "$REF"
cd "$SPARSE_PATH"

echo "Installing network-radio-server dependencies"
./install-deps.sh --assume-yes
echo "Rendering and deploying network-radio-server"
./deploy.sh
