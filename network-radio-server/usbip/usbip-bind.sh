#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="${USBIP_CONFIG:-/etc/usbip/devices.conf}"

if [[ ! -r "$CONFIG_FILE" ]]; then
  echo "usbip bind config not readable: $CONFIG_FILE" >&2
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

for busid in "${DEVICES[@]}"; do
  if usbip list -r "$SERVER" 2>/dev/null | grep -Fq "$busid"; then
    usbip bind -b "$busid" || true
    echo "bound $busid"
  else
    echo "skipped $busid; not present on $SERVER"
  fi
done
