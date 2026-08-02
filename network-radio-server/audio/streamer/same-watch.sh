#!/bin/bash

set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/network-radio-server}"
source "${INSTALL_ROOT}/generated.env"

if [[ "${SAME_ENABLED:-true}" != "true" ]]; then
    logger -t "${SAME_WATCH_TAG:-same-watch}" "SAME disabled by config"
    exit 0
fi

logger -t "${SAME_WATCH_TAG:-same-watch}" "starting SAME watch loop"

while true; do
    sleep 60
done
