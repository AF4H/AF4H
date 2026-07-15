#!/bin/bash

ffmpeg \
  -loglevel error \
  -i http://localhost:8000/WWH23 \
  -f s16le \
  -acodec pcm_s16le \
  -ac 1 \
  -ar 22050 \
  - 2>/dev/null | \
multimon-ng -q -a EAS -t raw - | \
while read -r line
do
    logger -t same-alert "$line"
    echo "$(date) $line" >> /var/log/same-alerts.log
    /usr/local/bin/same-act.sh "$line"
done
