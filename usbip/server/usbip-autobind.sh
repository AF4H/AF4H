#!/bin/bash

usbip list -l | while read -r line
do
    BUSID=$(echo "$line" | sed -n 's/^- busid \([^ ]*\).*/\1/p')

    if [[ "$BUSID" =~ ^1-1\.2(\.|$) ]]; then
        usbip bind -b "$BUSID" >/dev/null 2>&1
    fi
done
