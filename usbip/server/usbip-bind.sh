#!/bin/bash

modprobe usbip_host

# Example. Get Bus ID from `usbip list -l` 
usbip bind -b 1-1.2.1
