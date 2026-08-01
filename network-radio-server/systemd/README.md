# Systemd Units

These are the host-side units for the x86 radio server bundle.

The deploy script installs them into `/etc/systemd/system/` and stages the
application files into `/opt/network-radio-server/`.

Installed units:

- `usbipd.service`
- `usbipd.service.d/override.conf`
- `usbip-bind.service`
- `usbip-bind.service.d/override.conf`
- `ser2net.service`
- `radio-audio.service`
- `network-radio-dashboard.service`
- `avahi-daemon.service.d/override.conf`

Keep environment-specific values out of the units when possible. Use
`/etc/ser2net.conf`, `/etc/usbip/devices.conf`, and host-local config files for
the device-specific details. `ser2net.conf` is generated from
`ser2net/port-map.tsv` during deployment, so edit the TSV rather than the
installed file.
