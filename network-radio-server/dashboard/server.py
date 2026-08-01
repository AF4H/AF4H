#!/usr/bin/env python3
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


ROOT = os.path.dirname(__file__)
SCHEMA = os.path.join(ROOT, "status-schema.json")


def run(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def unit_state(name):
    active = run(["systemctl", "is-active", name])
    enabled = run(["systemctl", "is-enabled", name])
    return {"name": name, "active": active or "unknown", "enabled": enabled or "unknown"}


def build_status():
    with open(SCHEMA, "r", encoding="utf-8") as fh:
        status = json.load(fh)

    status["host"]["name"] = run(["hostname"]) or status["host"]["name"]
    status["host"]["ip"] = run(["hostname", "-I"]).split()[0] if run(["hostname", "-I"]) else None
    status["host"]["uptime"] = run(["uptime", "-p"]) or None
    status["services"] = [unit_state(name) for name in ("usbipd", "ser2net", "avahi-daemon", "radio-audio")]
    status["usbip"]["bound_devices"] = []
    status["usbip"]["configured_devices"] = []
    status["serial"]["ports"] = []
    status["audio"]["mode"] = "bridge"
    status["audio"]["health"] = "unknown"
    return status


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/status", "/status.json"):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return

        body = json.dumps(build_status(), indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    port = int(os.environ.get("NETWORK_RADIO_SERVER_PORT", "8088"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
