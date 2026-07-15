#!/bin/bash

source /etc/usbip/devices.conf

modprobe vhci_hcd

while true
do
    ATTACHED=$(usbip port 2>/dev/null)

    for BUSID in "${DEVICES[@]}"
    do
        if ! echo "$ATTACHED" | grep -q "$BUSID"; then
            logger -t usbip-watchdog "Attaching $BUSID"
            usbip attach -r "$SERVER" -b "$BUSID" >/dev/null 2>&1
        fi
    done

    sleep 30
done
