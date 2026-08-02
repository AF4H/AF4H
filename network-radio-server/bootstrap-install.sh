#!/usr/bin/env bash

set -euo pipefail

REPO_URL="${1:-}"
REF="${2:-main}"
TMPDIR="$(mktemp -d)"

usage() {
  cat <<'EOF'
Usage: bootstrap-install.sh <repo-url> [ref]

Bootstraps a fresh host by installing minimal clone tooling first, then
fetching the repo, installing the full dependency set, and deploying.
EOF
}

if [[ -z "$REPO_URL" ]]; then
  usage
  exit 1
fi

trap 'rm -rf "$TMPDIR"' EXIT

source /etc/os-release

install_bootstrap_tools() {
  case "${ID:-}" in
    debian|ubuntu)
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y git ca-certificates curl
      ;;
    *)
      echo "unsupported distro for bootstrap: ${ID:-unknown}" >&2
      exit 1
      ;;
  esac
}

install_bootstrap_tools
git clone "$REPO_URL" "$TMPDIR/network-radio-server"
cd "$TMPDIR/network-radio-server"
git checkout "$REF"

./install-deps.sh --assume-yes
./deploy.sh
