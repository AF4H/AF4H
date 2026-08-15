#!/bin/bash

set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/network-radio-server}"
LOG_TAG="${SAME_ACTION_TAG:-same-act}"
ENV_FILE="${INSTALL_ROOT}/generated.env"

log() {
    logger -t "$LOG_TAG" "$1"
}

die() {
    log "fatal: $1"
    exit 1
}

trap 'log "stopping on signal"; exit 0' INT TERM

[[ -r "$ENV_FILE" ]] || die "missing runtime config: $ENV_FILE"
source "$ENV_FILE"

if [[ "${SAME_ENABLED:-true}" != "true" ]]; then
    log "SAME disabled by config"
    exit 0
fi

log "starting SAME alert action loop"

while true; do
    sleep 60 &
    wait $!
done
