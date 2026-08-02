#!/bin/bash

usbip list -l | while read -r line
do
    case "$line" in
        *"1-1.2.4."*)
            BUSID=$(awk '{print $2}' <<<"$line")
            usbip bind -b "$BUSID" >/dev/null 2>&1
            ;;
    esac
done
