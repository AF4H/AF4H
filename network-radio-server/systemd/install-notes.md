# Install Notes

These files are meant to be installed on the x86 host, not run directly from
the repo.

Suggested destinations:

- `generated/systemd/*.service` -> `/etc/systemd/system/`
- `generated/dropins/systemd/usbip-bind.service.d/override.conf` ->
  `/etc/systemd/system/usbip-bind.service.d/override.conf`
- `generated/dropins/systemd/avahi-daemon.service.d/override.conf` ->
  `/etc/systemd/system/avahi-daemon.service.d/override.conf`
- `generated/rules/udev/usbip-bind.rules` ->
  `/etc/udev/rules.d/99-network-radio-server-usbip.rules`
- `generated/rules/usbip/server/99-usbip-autobind.rules` ->
  `/etc/udev/rules.d/99-usbip-autobind.rules`
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

The generated long-running services now include a shared hardening baseline
(`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`, `ProtectHome`, `KillSignal`,
and `TimeoutStopSec`) so the installed units stop cleanly and have less access
to the host.

The dashboard service is now an operator surface, not just a status stub. It
can:

- show the manifest summary and current service state
- rerender generated artifacts from `config.yaml`
- re-run the normal deploy path to apply changes and restart/re-enable units

That means the same `config.yaml` drives both shell-based installs and the web
UI path.

Package list to expect:

- `ser2net`
- `usbip`
- `avahi-daemon`
- `python3`
- `python3-venv` if you want the dashboard isolated
- `udev`
