#!/bin/bash

set -euo pipefail

source /opt/network-radio-server/generated.env

if [[ "${AUDIO_BRIDGE_ENABLED:-true}" != "true" ]]; then
    logger -t "${AUDIO_BRIDGE_LOGGER_TAG:-radio-audio}" "audio bridge disabled by config"
    exit 0
fi

logger -t "${AUDIO_BRIDGE_LOGGER_TAG:-radio-audio}" "starting ${AUDIO_BRIDGE_MODE:-placeholder} audio bridge"

while true; do
    sleep 60
done
