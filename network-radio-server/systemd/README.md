# Systemd Units

These are the host-side systemd artifacts for the x86 radio server bundle.

The manifest renders the core units into `generated/systemd/` and the deploy
script installs them into `/etc/systemd/system/`. The manifest also renders the
drop-ins and rules under `generated/dropins/` and `generated/rules/`, so the
remaining checked-in files here are just the documentation for that layout.

The dashboard backend reads the same manifest and exposes `/api/manifest`,
`/api/status`, `/api/render`, and `/api/apply` so the future web UI can inspect
and operate the same single source of truth instead of maintaining a parallel
control path.

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
`ser2net.conf`, `usbip/devices.conf`, the generated systemd units, and the
generated drop-ins/rules are all derived from `config.yaml` during deployment.
