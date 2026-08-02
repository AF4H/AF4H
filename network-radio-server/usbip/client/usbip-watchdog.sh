#!/usr/bin/env bash

set -euo pipefail

source /etc/usbip/devices.conf

while true; do
    ATTACHED=$(usbip port 2>/dev/null)
    for BUSID in "${DEVICES[@]}"; do
        if ! grep -q "$BUSID" <<<"$ATTACHED"; then
            logger -t usbip-watchdog "Attaching $BUSID"
            usbip attach -r "$SERVER" -b "$BUSID" >/dev/null 2>&1
        fi
    done
    sleep 30
done
