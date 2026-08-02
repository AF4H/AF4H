# Install Notes

These files are meant to be installed on the x86 host, not run directly from
the repo.

Suggested destinations:

- `systemd/usbip-bind.service.d/override.conf` ->
  `/etc/systemd/system/usbip-bind.service.d/override.conf`
- `systemd/avahi-daemon.service.d/override.conf` ->
  `/etc/systemd/system/avahi-daemon.service.d/override.conf`
- `generated/systemd/*.service` -> `/etc/systemd/system/`
- `udev/usbip-bind.rules` ->
  `/etc/udev/rules.d/99-network-radio-server-usbip.rules`
- `ser2net/ser2net.conf.example` -> reference output from the renderer
- `config.yaml` -> canonical manifest for all NRS generated config
- `ser2net/port-map.tsv` -> generated inventory for `ser2net`
- `usbip/client/etc/usbip/devices.conf` -> `/etc/usbip/devices.conf`
- `audio/*` -> `/opt/network-radio-server/audio`
- `audio/streamer/*` -> `/opt/network-radio-server/audio/streamer`
- `dashboard/*` -> `/opt/network-radio-server/dashboard`
- `usbip/usbip-bind.sh` -> `/usr/local/bin/usbip-bind.sh`
- `usbip/client/*` -> `/usr/local/bin/`

Use `deploy.sh` from the repo root to stage the bundle and enable the services.
The deploy script renders `/etc/ser2net.conf` and `/etc/usbip/devices.conf`
from `config.yaml` at install time, so the manifest is the thing to edit for
port or device changes.

Package list to expect:

- `ser2net`
- `usbip`
- `avahi-daemon`
- `python3`
- `python3-venv` if you want the dashboard isolated
- `udev`
