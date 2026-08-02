#!/usr/bin/env bash

set -euo pipefail

REPO_URL="${1:-}"
REF="${2:-main}"

if [[ -z "$REPO_URL" ]]; then
  echo "Usage: $0 <repo-url> [ref]" >&2
  exit 1
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

git clone "$REPO_URL" "$TMPDIR/network-radio-server"
cd "$TMPDIR/network-radio-server"
git checkout "$REF"

./install-deps.sh --assume-yes
./deploy.sh

