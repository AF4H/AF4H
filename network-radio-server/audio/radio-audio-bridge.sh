#!/bin/bash

set -euo pipefail

# Placeholder audio bridge for the radio server.
# This is intentionally conservative: it keeps the service structure in place
# without hardcoding a final audio topology yet.

logger -t radio-audio "starting placeholder audio bridge"

while true; do
    sleep 60
done
