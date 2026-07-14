#!/bin/bash

modprobe vhci_hcd

sleep 5

# Example. Get Bus IDs from `usbip list -r x.x.x.x`
usbip attach -r x.x.x.x -b 1-1.2.1
