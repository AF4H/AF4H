#!/usr/bin/env bash

set -euo pipefail

source /etc/usbip/devices.conf

for BUSID in "${DEVICES[@]}"; do
    usbip attach -r "$SERVER" -b "$BUSID"
done
