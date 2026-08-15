#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="${USBIP_CONFIG:-/etc/usbip/devices.conf}"

if [[ ! -r "$CONFIG_FILE" ]]; then
    echo "usbip watchdog config not readable: $CONFIG_FILE" >&2
    exit 1
fi

source "$CONFIG_FILE"

if [[ -z "${SERVER:-}" ]]; then
    echo "missing SERVER in $CONFIG_FILE" >&2
    exit 1
fi

if [[ "${#DEVICES[@]}" -eq 0 ]]; then
    echo "no DEVICES listed in $CONFIG_FILE" >&2
    exit 0
fi

while true; do
    ATTACHED=$(PATH=/usr/sbin:/usr/bin:/sbin:/bin usbip port 2>/dev/null || true)
    for BUSID in "${DEVICES[@]}"; do
        if ! grep -q "$BUSID" <<<"$ATTACHED"; then
            if PATH=/usr/sbin:/usr/bin:/sbin:/bin usbip list -r "$SERVER" 2>/dev/null | grep -Fq "$BUSID"; then
                logger -t usbip-watchdog "Attaching $BUSID"
                PATH=/usr/sbin:/usr/bin:/sbin:/bin usbip attach -r "$SERVER" -b "$BUSID" >/dev/null 2>&1 || true
            fi
        fi
    done
    sleep 30
done
