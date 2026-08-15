#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="${USBIP_CONFIG:-/etc/usbip/devices.conf}"

if [[ ! -r "$CONFIG_FILE" ]]; then
    echo "usbip attach config not readable: $CONFIG_FILE" >&2
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

for BUSID in "${DEVICES[@]}"; do
    if ! PATH=/usr/sbin:/usr/bin:/sbin:/bin usbip list -r "$SERVER" 2>/dev/null | grep -Fq "$BUSID"; then
        echo "skipped $BUSID; not present on $SERVER"
        continue
    fi
    PATH=/usr/sbin:/usr/bin:/sbin:/bin usbip attach -r "$SERVER" -b "$BUSID" || true
done
