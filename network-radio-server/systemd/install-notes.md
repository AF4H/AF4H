# Install Notes

These files are meant to be installed on the x86 host, not run directly from
the repo.

Suggested destinations:

- `systemd/usbip-bind.service.d/override.conf` ->
  `/etc/systemd/system/usbip-bind.service.d/override.conf`
- `systemd/avahi-daemon.service.d/override.conf` ->
  `/etc/systemd/system/avahi-daemon.service.d/override.conf`
- `udev/usbip-bind.rules` ->
  `/etc/udev/rules.d/99-network-radio-server-usbip.rules`
- `ser2net/ser2net.conf.example` -> reference output from the renderer
- `ser2net/port-map.tsv` -> source inventory for `ser2net`
- `ser2net/render-ser2net.sh` -> helper that generates `/etc/ser2net.conf`
- `usbip/server/*.service` -> `/etc/systemd/system/`
- `usbip/client/*.service` -> `/etc/systemd/system/`
- `usbip/client/etc/usbip/devices.conf` -> `/etc/usbip/devices.conf`
- `audio/*` -> `/opt/network-radio-server/audio`
- `audio/streamer/*` -> `/opt/network-radio-server/audio/streamer`
- `dashboard/*` -> `/opt/network-radio-server/dashboard`
- `ser2net/*` -> `/opt/network-radio-server/ser2net`
- `usbip/usbip-bind.sh` -> `/usr/local/bin/usbip-bind.sh`
- `usbip/client/*` -> `/usr/local/bin/`

Use `deploy.sh` from the repo root to stage the bundle and enable the services.
The deploy script renders `/etc/ser2net.conf` from `ser2net/port-map.tsv` at
install time, so the TSV is the thing to edit for port changes.

Package list to expect:

- `ser2net`
- `usbip`
- `avahi-daemon`
- `python3`
- `python3-venv` if you want the dashboard isolated
- `udev`
