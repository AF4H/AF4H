#!/bin/bash

source /etc/usbip/devices.conf

modprobe vhci_hcd

for BUSID in "${DEVICES[@]}"
do
    usbip attach -r "$SERVER" -b "$BUSID"
done
