#!/bin/bash

RAW="$*"

logger -t same-alert "$RAW"

echo "$(date '+%F %T')|RAW|$RAW" >> /var/log/same-alerts.log

# Extract the SAME string
MSG=$(echo "$RAW" | sed -n 's/.*ZCZC-\(.*\)/\1/p')

[ -z "$MSG" ] && exit 0

ORIGINATOR=$(echo "$MSG" | cut -d- -f1)
EVENT=$(echo "$MSG" | cut -d- -f2)
FIPS=$(echo "$MSG" | cut -d- -f3)
DURATION=$(echo "$MSG" | cut -d- -f4 | tr -d '+')

echo "$(date '+%F %T')|EVENT=$EVENT|FIPS=$FIPS|DURATION=$DURATION" \
    >> /var/log/same-events.log

case "$EVENT" in
    TOR)
        logger -t same-alert "TORNADO WARNING"
        ;;
    SVR)
        logger -t same-alert "SEVERE THUNDERSTORM WARNING"
        ;;
    FFW)
        logger -t same-alert "FLASH FLOOD WARNING"
        ;;
    RWT)
        logger -t same-alert "REQUIRED WEEKLY TEST"
        ;;
    EAN)
        logger -t same-alert "EMERGENCY ACTION NOTIFICATION"
        ;;
esac
