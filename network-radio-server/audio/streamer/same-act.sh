#!/bin/bash

set -euo pipefail

source /opt/network-radio-server/generated.env

if [[ "${SAME_ENABLED:-true}" != "true" ]]; then
    logger -t "${SAME_ACTION_TAG:-same-act}" "SAME disabled by config"
    exit 0
fi

logger -t "${SAME_ACTION_TAG:-same-act}" "starting SAME alert action loop"

while true; do
    sleep 60
done
