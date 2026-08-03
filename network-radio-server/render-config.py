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


def render_avahi_service(avahi: dict) -> str:
    return "\n".join(
        [
            '<?xml version="1.0" standalone="no"?>',
            '<!DOCTYPE service-group SYSTEM "avahi-service.dtd">',
            '<service-group>',
            f'  <name replace-wildcards="yes">{avahi["display_name"]}</name>',
            '  <service>',
            '    <type>_http._tcp</type>',
            f'    <port>{avahi.get("port", 0)}</port>',
            f'    <txt-record>description={avahi["description"]}</txt-record>',
            f'    <txt-record>service={avahi["service_name"]}</txt-record>',
            '  </service>',
            '</service-group>',
            "",
        ]
    )


def render_unit(name: str, unit: dict) -> str:
    lines = ["[Unit]", f"Description={unit['description']}"]
    after = unit.get("after", [])
    if after:
        lines.append("After=" + " ".join(after))
    wants = unit.get("wants", [])
    if wants:
        lines.append("Wants=" + " ".join(wants))
    lines.append("")
    lines.append("[Service]")
    lines.append(f"Type={unit.get('type', 'simple')}")
    if "working_directory" in unit:
        lines.append(f"WorkingDirectory={unit['working_directory']}")
    lines.append(f"ExecStart={unit['exec_start']}")
    if "pid_file" in unit:
        lines.append(f"PIDFile={unit['pid_file']}")
    if unit.get("remain_after_exit"):
        lines.append("RemainAfterExit=yes")
    restart = unit.get("restart")
    if restart:
        lines.append(f"Restart={restart}")
    if "restart_sec" in unit:
        lines.append(f"RestartSec={unit['restart_sec']}")
    lines.append("")
    lines.append("[Install]")
    lines.append("WantedBy=multi-user.target")
    lines.append("")
    return "\n".join(lines)


def render_target(description: str, wants: list[str], after: list[str]) -> str:
    lines = ["[Unit]", f"Description={description}"]
    if after:
        lines.append("After=" + " ".join(after))
    if wants:
        lines.append("Wants=" + " ".join(wants))
    lines.append("")
    lines.append("[Install]")
    lines.append("WantedBy=multi-user.target")
    lines.append("")
    return "\n".join(lines)


def render_text_block(content: str) -> str:
    return content.rstrip("\n") + "\n"


def unit_filename(key: str) -> str:
    return f"{key.replace('_', '-')}.service"


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
    avahi = manifest.get("avahi", {})
    if avahi.get("enabled", False):
        (ROOT / "avahi" / "radio-server.service").write_text(render_avahi_service(avahi), encoding="utf-8")
    generated_systemd = ROOT / "generated" / "systemd"
    generated_systemd.mkdir(parents=True, exist_ok=True)
    for name, unit in manifest.get("systemd", {}).items():
        (generated_systemd / unit_filename(name)).write_text(render_unit(name, unit), encoding="utf-8")
    if services.get("network_radio_server_target", True):
        target_units = [
            "usbipd.service",
            "usbip-bind.service",
            "usbip-attach.service",
            "usbip-watchdog.service",
            "ser2net.service",
            "radio-audio.service",
            "radio-audio-streamer.service",
            "network-radio-dashboard.service",
        ]
        (generated_systemd / "network-radio-server.target").write_text(
            render_target("Network Radio Server Stack", target_units, target_units),
            encoding="utf-8",
        )
    generated_dropins = ROOT / "generated" / "dropins"
    generated_dropins.mkdir(parents=True, exist_ok=True)
    for entry in manifest.get("dropins", {}).values():
        (generated_dropins / entry["path"]).parent.mkdir(parents=True, exist_ok=True)
        (generated_dropins / entry["path"]).write_text(render_text_block(entry["content"]), encoding="utf-8")
    generated_rules = ROOT / "generated" / "rules"
    generated_rules.mkdir(parents=True, exist_ok=True)
    for entry in manifest.get("rules", {}).values():
        (generated_rules / entry["path"]).parent.mkdir(parents=True, exist_ok=True)
        (generated_rules / entry["path"]).write_text(render_text_block(entry["content"]), encoding="utf-8")
    (ROOT / "generated.env").write_text(
        "\n".join(
            [
                f"ENABLE_SER2NET={str(bool(services.get('ser2net', True))).lower()}",
                f"ENABLE_RADIO_AUDIO={str(bool(services.get('radio_audio', True))).lower()}",
                f"ENABLE_RADIO_AUDIO_STREAMER={str(bool(services.get('radio_audio_streamer', True))).lower()}",
                f"ENABLE_NETWORK_RADIO_DASHBOARD={str(bool(services.get('network_radio_dashboard', True))).lower()}",
                f"ENABLE_NETWORK_RADIO_SERVER_TARGET={str(bool(services.get('network_radio_server_target', True))).lower()}",
                f"ENABLE_USBIPD={str(bool(services.get('usbipd', True))).lower()}",
                f"ENABLE_USBIP_BIND={str(bool(services.get('usbip_bind', True))).lower()}",
                f"ENABLE_USBIP_ATTACH={str(bool(services.get('usbip_attach', True))).lower()}",
                f"ENABLE_USBIP_WATCHDOG={str(bool(services.get('usbip_watchdog', True))).lower()}",
                f"INSTALL_ROOT={manifest.get('defaults', {}).get('install_root', '/opt/network-radio-server')}",
                f"AUDIO_BRIDGE_ENABLED={str(bool(manifest.get('audio', {}).get('bridge', {}).get('enabled', True))).lower()}",
                f"AUDIO_BRIDGE_MODE={manifest.get('audio', {}).get('bridge', {}).get('mode', 'placeholder')}",
                f"AUDIO_BRIDGE_LOGGER_TAG={manifest.get('audio', {}).get('bridge', {}).get('logger_tag', 'radio-audio')}",
                f"AUDIO_ADAPTER_COUNT={len(manifest.get('audio', {}).get('adapters', []))}",
                "AUDIO_ADAPTERS=" + ",".join(a.get("name", "") for a in manifest.get("audio", {}).get("adapters", [])),
                f"STREAMER_COUNT={len(manifest.get('audio', {}).get('streamers', []))}",
                "AUDIO_STREAMERS=" + ",".join(s.get("name", "") for s in manifest.get("audio", {}).get("streamers", [])),
                "AUDIO_TRANSPORTS=" + ",".join(t.get("name", "") for t in manifest.get("audio", {}).get("transports", [])),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
