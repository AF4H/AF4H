#!/bin/bash

set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/network-radio-server}"
source "${INSTALL_ROOT}/generated.env"

if [[ "${AUDIO_STREAMER_ENABLED:-true}" != "true" ]]; then
    logger -t "${AUDIO_STREAMER_LOGGER_TAG:-WWH23-feed}" "streamer disabled by config"
    exit 0
fi

logger -t "${AUDIO_STREAMER_LOGGER_TAG:-WWH23-feed}" "starting weather radio feed"

while true; do
    sleep 60
done
