#!/bin/bash

set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/network-radio-server}"
LOG_TAG="${AUDIO_BRIDGE_LOGGER_TAG:-radio-audio}"
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

if [[ "${AUDIO_BRIDGE_ENABLED:-true}" != "true" ]]; then
    log "audio bridge disabled by config"
    exit 0
fi

log "starting ${AUDIO_BRIDGE_MODE:-placeholder} audio bridge"

while true; do
    sleep 60 &
    wait $!
done
