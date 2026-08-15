#!/bin/bash

set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/network-radio-server}"
LOG_TAG="${AUDIO_STREAMER_LOGGER_TAG:-WWH23-feed}"
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

if [[ "${AUDIO_STREAMER_ENABLED:-true}" != "true" ]]; then
    log "streamer disabled by config"
    exit 0
fi

log "starting weather radio feed"

while true; do
    sleep 60 &
    wait $!
done
