#!/bin/bash

modprobe usbip_host

# USB Audio adapter (Wx)
usbip bind -b 1-1.2.4.1

# IC-7100
usbip bind -b 1-1.2.4.4.1
usbip bind -b 1-1.2.4.4.2
usbip bind -b 1-1.2.4.4.3
