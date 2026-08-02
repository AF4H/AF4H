#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to render network-radio-server config") from exc


ROOT = Path(__file__).resolve().parent


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise SystemExit("config must be a mapping")
    return data


def render_ser2net(entries: list[dict]) -> str:
    lines = [
        "# Example ser2net configuration for AF4H radio and serial ports.",
        "# Generated from `config.yaml` via `render-config.py`.",
        "# Edit the manifest, then regenerate this file so the docs and config stay in lockstep.",
        "",
    ]
    seen = set()
    for row in entries:
        port = int(row["port"])
        if port in seen:
            raise SystemExit(f"duplicate port in inventory: {port}")
        seen.add(port)
        device = row["device"]
        baud = row["baud"]
        fmt = str(row.get("format", "8N1")).lower()
        flow = str(row.get("flow", "-")).strip()
        notes = str(row.get("notes", "")).strip()
        lines += [
            f"connection: &port_{port}",
            f"  accepter: tcp,{port}",
            f"  connector: serialdev,{device},{baud} {fmt},local"
            + (",rtscts" if flow == "rtscts" else ""),
            "  options:",
            "    kickolduser: true",
        ]
        if notes:
            lines.append(f"  # {notes}")
        lines.append("")
    return "\n".join(lines)


def render_usbip(conf: dict) -> str:
    server = conf["server"]
    devices = [d for d in conf.get("devices", []) if d.get("enabled", True)]
    lines = [f"SERVER={server}", "", "DEVICES=("]
    for device in devices:
        busid = device["busid"]
        name = device.get("name", "")
        suffix = f" # {name}" if name else ""
        lines.append(f'\t"{busid}"{suffix}')
    lines.append(")")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    manifest = load_config(ROOT / "config.yaml")
    ser2net = render_ser2net(manifest.get("ser2net", []))
    usbip = render_usbip(manifest["usbip"])
    services = manifest.get("services", {})

    (ROOT / "ser2net" / "port-map.tsv").write_text(
        "port\tdevice\tbaud\tformat\tflow\tnotes\n"
        + "\n".join(
            f"{row['port']}\t{row['device']}\t{row['baud']}\t{row.get('format', '8N1')}\t{row.get('flow', '-')}\t{row.get('notes', '')}"
            for row in manifest.get("ser2net", [])
        )
        + "\n",
        encoding="utf-8",
    )
    (ROOT / "ser2net" / "ser2net.conf.example").write_text(ser2net, encoding="utf-8")
    (ROOT / "usbip" / "devices.conf.example").write_text(usbip, encoding="utf-8")
    (ROOT / "generated.env").write_text(
        "\n".join(
            [
                f"ENABLE_SER2NET={str(bool(services.get('ser2net', True))).lower()}",
                f"ENABLE_RADIO_AUDIO={str(bool(services.get('radio_audio', True))).lower()}",
                f"ENABLE_RADIO_AUDIO_STREAMER={str(bool(services.get('radio_audio_streamer', True))).lower()}",
                f"ENABLE_NETWORK_RADIO_DASHBOARD={str(bool(services.get('network_radio_dashboard', True))).lower()}",
                f"ENABLE_USBIPD={str(bool(services.get('usbipd', True))).lower()}",
                f"ENABLE_USBIP_BIND={str(bool(services.get('usbip_bind', True))).lower()}",
                f"ENABLE_USBIP_ATTACH={str(bool(services.get('usbip_attach', True))).lower()}",
                f"ENABLE_USBIP_WATCHDOG={str(bool(services.get('usbip_watchdog', True))).lower()}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
