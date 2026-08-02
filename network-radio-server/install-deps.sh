#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install-deps.sh [--assume-yes]

Install packages needed to render and deploy network-radio-server.
Extending to a new distro means adding a new case block below.
EOF
}

assume_yes=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--assume-yes)
      assume_yes=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

source /etc/os-release

install_debian() {
  local packages=(
    python3
    python3-yaml
    ser2net
    usbip
    avahi-daemon
    udev
    curl
    git
  )
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y "${packages[@]}"
}

install_ubuntu() {
  install_debian
}

case "${ID:-}" in
  debian)
    install_debian
    ;;
  ubuntu)
    install_ubuntu
    ;;
  *)
    echo "unsupported distro: ${ID:-unknown}" >&2
    exit 1
    ;;
esac

