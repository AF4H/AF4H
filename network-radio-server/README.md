# Network Radio Interconnection Server

This directory describes the x86 host that bridges radios and ham workstation
services over the network.

## Goals

- Export selected USB devices with `usbip` and a udev-triggered bind helper
- Provide serial CAT and programming access with `ser2net`
- Advertise the host and services with `avahi`
- Stream or bridge radio audio for WSJT-X, SAME alerting, and related tools
- Expose service status through a later dashboard

## Host Assumption

The design is aimed at a small x86 system rather than a Raspberry Pi. That
fits the larger USB serial hub count better and leaves more headroom for
additional radios and interfaces over time.

## Quick Install

1. Edit `config.yaml` for the target host.
2. Run `./deploy.sh` from the repo root on the host.
3. Review `/etc/ser2net.conf`, `/etc/usbip/devices.conf`, and the enabled
   systemd units.
4. Start the enabled services with `systemctl start network-radio-server.target`.

If you prefer the browser workflow, the dashboard at `/` can edit the most
common manifest fields, validate the result, then save, render, and apply from
the same `config.yaml`.

## Recommended Layout

- `generated/systemd/` - generated service units from the manifest
- `systemd/` - service drop-ins and exceptions for host startup
- `config.yaml` - canonical manifest for ports, USB/IP, and audio flags
- `ser2net/` - generated `ser2net` configuration examples
- `usbip/` - generated device inventory and bind rules
- `avahi/` - mDNS service definitions
- `audio/` - audio bridge scripts and notes, plus `audio/streamer/`
- `dashboard/` - web status/apply UI and JSON API, including validation and
  a structured manifest editor

## Suggested Operating Model

1. The host boots and starts `usbipd`, `ser2net`, `avahi-daemon`, and the audio
   bridge services.
2. USB devices that should be shared are bound to `usbip` via the bind helper
   and a udev rule.
3. Serial radios are exposed on stable TCP ports through `ser2net`.
4. Audio is routed to a local sink or stream endpoint used by WSJT-X workflows,
   weather-radio monitoring, and SAME alerting.
5. A dashboard can read service state from `systemctl`, `usbip`, and health
   endpoints, and can feed validated edits back into the same manifest.

## Repo Notes

The bundle includes the manifest, deploy script, generated inventory artifacts,
and a small set of non-generated drop-ins needed to stage a working host
without rebuilding the whole system from scratch.

The installed host mirrors the management entrypoints under
`/opt/network-radio-server/` as well, so you can inspect or re-run the deploy
and renderer scripts from the target machine after bootstrap. The host also
gets `/opt/network-radio-server/README-host.md` as a quick local reference.

## Ser2net Inputs Needed

To add or change serial devices, capture one block of details per radio or USB
serial device:

- friendly name
  - device path on the host, such as `/dev/ttyUSB0` or `/dev/serial/by-id/...`
- baud rate
- data bits, parity, and stop bits
- whether hardware flow control is required
- the TCP port you want exposed
- whether it is CAT control, firmware/programming, or both

The safer choice is to use `/dev/serial/by-id/...` paths when available so the
mapping survives USB replugging.

## Current Ser2net Inventory

The following devices are mapped in `ser2net/ports.md` and derived from
`config.yaml`:

- 3 general console / radio serial ports at `115200 8N1`
- 1 router console at `115200 8N1`
- 2 IC-7100 CAT ports at `19200 8N1`

The `7301`-`7303` ports are general-purpose serial ports. Change the inventory
if you want a different layout before turning the host into the source of
truth.

## Port Bands

Use these ranges as the default layout going forward:

- `72xx` - TNCs, modems, packet gear, and similar data devices
- `73xx` - serial console ports and general-purpose radio serial interfaces
- `75xx` - miscellaneous serial devices like displays, signs, and utilities

Default baud for the `73xx` console band should be `115200`.

The main benefit is predictability: once you have a handful of devices, the
port number tells you the class of device before you even connect.

## Inventory Conventions

- `-` in the `flow` column means no special flow control is required.
- Use `/dev/serial/by-id/...` whenever possible so the mapping survives USB
  replugging.
- The generated `/etc/ser2net.conf` is the install-time output of
  `config.yaml`, not a hand-edited file.
- Generated systemd units live under `generated/systemd/` and should also be
  treated as manifest output.

## Build Order

1. Install the host packages and drop the `systemd` units into place.
2. Load the `ser2net` configuration using the chosen TCP port plan.
3. Bring up the dashboard backend last so it reflects the final service names
   and paths instead of placeholders.
