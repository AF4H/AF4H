#!/usr/bin/env bash

set -euo pipefail

REF="${REF:-main}"
TMPDIR="$(mktemp -d)"
REPO_URL="https://github.com/AF4H/AF4H.git"
SPARSE_PATH="network-radio-server"

trap 'rm -rf "$TMPDIR"' EXIT

source /etc/os-release

preflight() {
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
install_bootstrap_tools

git clone --filter=blob:none --sparse "$REPO_URL" "$TMPDIR/AF4H"
cd "$TMPDIR/AF4H"
git sparse-checkout set "$SPARSE_PATH"
git checkout "$REF"
cd "$SPARSE_PATH"

./install-deps.sh --assume-yes
./deploy.sh
