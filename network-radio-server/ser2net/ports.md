# ser2net Port Map

`port-map.tsv` is the source of truth. This file is the readable view of that
inventory and should stay in lockstep with the TSV and generated config.
In the TSV, `-` in the flow column means no special flow control is required.

## Serial Console / Radio Ports

- `7301` - `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`
- `7302` - `/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AR0KHLQA-if00-port0`
- `7303` - `/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0`

Assumed settings:

- `115200 8N1`
- local console or radio serial use

## TNC / Modem / Data Gear

- `7201` - reserved
- `7202` - reserved
- `7203` - reserved

Use this band for TNCs, packet gear, modems, APRS interfaces, and other data
devices.

## Router Console

- `7310` - `/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0`

Settings:

- `115200 8N1`
- console access

## IC-7100 CAT

- `7304` - `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_IC-7100_02015445_A-if00-port0`
- `7305` - `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_IC-7100_02015445_B-if00-port0`

Settings:

- `19200 8N1`
- CAT control

## Misc Devices

- `7501` and up - LED signs, service utilities, lab controllers, and other
  one-off serial gear

## Notes

- If any radio needs hardware flow control, add `rtscts` to the serial options.
- If any interface needs a different baud rate, update the matching inventory
  row in `port-map.tsv` and regenerate the config.
- If a new device does not fit the usual bands, assign it a block once and keep
  it there so the port map stays readable.
