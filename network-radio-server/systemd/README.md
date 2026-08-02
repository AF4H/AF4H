# Systemd Units

These are the host-side systemd artifacts for the x86 radio server bundle.

The manifest renders the core units into `generated/systemd/` and the deploy
script installs them into `/etc/systemd/system/`. The remaining files in this
directory are drop-ins and exceptions.

Generated units:

- `ser2net.service`
- `usbipd.service`
- `usbip-bind.service`
- `usbip-attach.service`
- `usbip-watchdog.service`
- `radio-audio.service`
- `radio-audio-streamer.service`
- `network-radio-dashboard.service`

Keep environment-specific values out of the units when possible. Use the
manifest and the generated config files for the device-specific details.
`ser2net.conf`, `usbip/devices.conf`, and the enabled systemd units are all
derived from `config.yaml` during deployment.
