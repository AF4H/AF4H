# Audio Bridge Notes

This folder is for the audio side of the radio server.

## Current Repo Hints

- `audio/streamer/WWH23-feed.sh`
- `audio/streamer/same-act.sh`
- `audio/streamer/same-watch.sh`

## Recommended First Pass

For WSJT-X use, the cleanest approach is usually:

- ALSA loopback for a simple, predictable audio path
- or PipeWire/PulseAudio virtual devices if the host already uses that stack

Keep the first version boring. Low-latency and easy to debug matters more than
clever routing.

## Where To Put The Bridge

- `audio/radio-audio-bridge.sh` is the placeholder service entrypoint
- `audio/radio-audio.service` is the matching systemd unit
- `audio/streamer/` holds the weather-radio and general streamer helpers

Replace the placeholder loop with the real mixer/bridge once you pick the audio
topology.
