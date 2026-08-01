# Ser2net Port Map Template

Use this template to allocate stable TCP ports before filling in the final
`ser2net.conf`.

## `72xx` - TNCs, Modems, and Data Gear

| TCP Port | Device | Notes |
| --- | --- | --- |
| 7201 |  | Reserved for TNC / packet gear |
| 7202 |  | Reserved for modem or APRS hardware |
| 7203 |  | Reserved for data interfaces |
| 7204 |  | Spare |
| 7205 |  | Spare |
| 7206 |  | Spare |
| 7207 |  | Spare |
| 7208 |  | Spare |
| 7209 |  | Spare |

## `73xx` - Consoles and General Radio Serial

| TCP Port | Device | Baud / Format | Notes |
| --- | --- | --- | --- |
| 7301 |  | 115200 8N1 | Console or radio serial |
| 7302 |  | 115200 8N1 | Console or radio serial |
| 7303 |  | 115200 8N1 | Console or radio serial |
| 7304 |  | 19200 8N1 | IC-7100 CAT or similar |
| 7305 |  | 19200 8N1 | IC-7100 CAT or similar |
| 7306 |  | 115200 8N1 | Spare |
| 7307 |  | 115200 8N1 | Spare |
| 7308 |  | 115200 8N1 | Spare |
| 7309 |  | 115200 8N1 | Spare |
| 7310 |  | 115200 8N1 | Router or infrastructure console |

## `75xx` - Miscellaneous Serial Devices

| TCP Port | Device | Baud / Format | Notes |
| --- | --- | --- | --- |
| 7501 |  |  | LED signs, controllers, and one-off gear |
| 7502 |  |  | Spare |
| 7503 |  |  | Spare |
| 7504 |  |  | Spare |
| 7505 |  |  | Spare |
| 7506 |  |  | Spare |
| 7507 |  |  | Spare |
| 7508 |  |  | Spare |
| 7509 |  |  | Spare |
| 7510 |  |  | Spare |

## Notes

- Prefer `/dev/serial/by-id/...` paths in the final config.
- Keep a single device in a single port block once assigned.
- If hardware flow control is needed, add `rtscts`.
