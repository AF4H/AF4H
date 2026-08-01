#!/usr/bin/env bash

set -euo pipefail

INPUT="${1:-$(dirname "$0")/port-map.tsv}"

awk -F'\t' '
  BEGIN {
    print "# Example ser2net configuration for AF4H radio and serial ports."
    print "# Generated from port-map.tsv. Edit the inventory, not this file."
    print ""
  }
  NR == 1 { next }
  NF < 5 { next }
  {
    port = $1
    device = $2
    baud = $3
    fmt = tolower($4)
    flow = $5
    notes = $6

    gsub(/^[ \t]+|[ \t]+$/, "", flow)
    gsub(/^[ \t]+|[ \t]+$/, "", notes)

    conn_name = "port_" port
    print "connection: &" conn_name
    print "  accepter: tcp," port

    connector = "serialdev," device "," baud " " fmt ",local"
    if (flow == "rtscts") {
      connector = connector ",rtscts"
    }
    print "  connector: " connector
    print "  options:"
    print "    kickolduser: true"
    if (notes != "") {
      print "  # " notes
    }
    print ""
    seen[port]++
  }
  END {
    for (port in seen) {
      if (seen[port] > 1) {
        printf "duplicate port in inventory: %s\n", port > "/dev/stderr"
        exit 1
      }
    }
  }
' "$INPUT"
