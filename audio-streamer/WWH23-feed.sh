#!/bin/bash

exec ffmpeg \
  -f alsa \
  -i plughw:CARD=Device,DEV=0 \
  -af "volume=12dB" \
  -ac 1 \
  -ar 44100 \
  -codec:a libmp3lame \
  -b:a 24k \
  -content_type audio/mpeg \
  -f mp3 \
  icecast://source:streemz@localhost:8000/WWH23
