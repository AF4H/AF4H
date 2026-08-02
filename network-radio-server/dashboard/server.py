#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to run the dashboard") from exc


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = Path(__file__).resolve().parent
MANIFEST = ROOT / "config.yaml"
GENERATED_ENV = ROOT / "generated.env"
RENDERER = ROOT / "render-config.py"
DEPLOY = ROOT / "deploy.sh"
STATUS_SCHEMA = DASHBOARD_DIR / "status-schema.json"


REQUIRED_TOP_LEVEL = {
    "version": int,
    "defaults": dict,
    "ser2net": list,
    "usbip": dict,
    "audio": dict,
    "systemd": dict,
    "avahi": dict,
    "services": dict,
    "dropins": dict,
    "rules": dict,
}


def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def run_capture(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, text=True, capture_output=True, cwd=str(ROOT))
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode == 0,
    }


def unit_state(name: str) -> dict:
    active = run(["systemctl", "is-active", name]) or "unknown"
    enabled = run(["systemctl", "is-enabled", name]) or "unknown"
    return {"name": name, "active": active, "enabled": enabled}


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False)


def canonical_yaml(data: dict) -> str:
    return dump_yaml(data).strip() + "\n"


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validation_errors(manifest: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest must be a YAML mapping at the top level"]

    for key, typ in REQUIRED_TOP_LEVEL.items():
        if key not in manifest:
            errors.append(f"missing required top-level key: {key}")
            continue
        if not isinstance(manifest[key], typ):
            errors.append(f"{key} must be a {typ.__name__}")

    if errors:
        return errors

    defaults = manifest.get("defaults", {})
    if not isinstance(defaults.get("install_root", ""), str) or not defaults.get("install_root"):
        errors.append("defaults.install_root must be a non-empty string")

    ser2net = manifest.get("ser2net", [])
    for idx, row in enumerate(ser2net):
        if not isinstance(row, dict):
            errors.append(f"ser2net[{idx}] must be a mapping")
            continue
        for field in ("port", "device", "baud", "format", "flow"):
            if field not in row:
                errors.append(f"ser2net[{idx}] missing {field}")

    usbip = manifest.get("usbip", {})
    if not isinstance(usbip.get("devices", []), list):
        errors.append("usbip.devices must be a list")

    audio = manifest.get("audio", {})
    if not isinstance(audio.get("streamers", []), list):
        errors.append("audio.streamers must be a list")
    if not isinstance(audio.get("transports", []), list):
        errors.append("audio.transports must be a list")

    services = manifest.get("services", {})
    if not any(bool(v) for v in services.values()):
        errors.append("services must enable at least one unit")

    return errors


def manifest_summary(manifest: dict) -> dict:
    audio = manifest.get("audio", {})
    return {
        "manifest_path": "config.yaml",
        "revision": file_hash(MANIFEST),
        "last_rendered": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(GENERATED_ENV.stat().st_mtime)) if GENERATED_ENV.exists() else None,
        "defaults": manifest.get("defaults", {}),
        "ser2net_count": len(manifest.get("ser2net", [])),
        "usbip_count": len([d for d in manifest.get("usbip", {}).get("devices", []) if d.get("enabled", True)]),
        "audio": {
            "bridge": audio.get("bridge", {}),
            "streamers": audio.get("streamers", []),
            "transports": audio.get("transports", []),
        },
        "avahi": manifest.get("avahi", {}),
        "services": manifest.get("services", {}),
        "systemd": manifest.get("systemd", {}),
        "dropins": manifest.get("dropins", {}),
        "rules": manifest.get("rules", {}),
    }


def build_status() -> dict:
    manifest = load_yaml(MANIFEST)
    schema = load_yaml(STATUS_SCHEMA) if STATUS_SCHEMA.suffix == ".yaml" else {}
    if not schema:
        with STATUS_SCHEMA.open("r", encoding="utf-8") as fh:
            schema = json.load(fh)

    status = dict(schema)
    hostname = run(["hostname"]) or status["host"]["name"]
    host_ip = run(["hostname", "-I"])
    status["host"]["name"] = hostname
    status["host"]["ip"] = host_ip.split()[0] if host_ip else None
    status["host"]["uptime"] = run(["uptime", "-p"]) or None
    status["host"]["reachable"] = True
    status["config"] = manifest_summary(manifest)
    status["services"] = [unit_state(name) for name in (
        "usbipd.service",
        "ser2net.service",
        "avahi-daemon.service",
        "radio-audio.service",
        "radio-audio-streamer.service",
        "network-radio-dashboard.service",
    )]
    status["usbip"]["server"] = manifest.get("usbip", {}).get("server")
    status["usbip"]["configured_devices"] = manifest.get("usbip", {}).get("devices", [])
    status["usbip"]["bound_devices"] = []
    status["serial"]["ports"] = manifest.get("ser2net", [])
    audio = manifest.get("audio", {})
    status["audio"]["mode"] = audio.get("bridge", {}).get("mode", "unknown")
    status["audio"]["health"] = "unknown"
    status["audio"]["streamers"] = audio.get("streamers", [])
    return status


def dashboard_page() -> bytes:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Network Radio Server</title>
  <style>
    :root {{
      --bg: #0b1020;
      --panel: #111936;
      --panel-2: #162044;
      --text: #e6ecff;
      --muted: #93a1c7;
      --accent: #7dd3fc;
      --danger: #fb7185;
      --ok: #86efac;
    }}
    body {{
      margin: 0;
      font-family: system-ui, sans-serif;
      background: radial-gradient(circle at top, #162044 0, var(--bg) 55%);
      color: var(--text);
    }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 24px; }}
    .grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); }}
    .card {{ background: rgba(17, 25, 54, 0.92); border: 1px solid rgba(125, 211, 252, 0.18); border-radius: 16px; padding: 16px; }}
    .stack {{ display: grid; gap: 10px; }}
    .row {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
    .muted {{ color: var(--muted); }}
    h1, h2, h3 {{ margin-top: 0; }}
    input, select, textarea {{
      width: 100%;
      box-sizing: border-box;
      background: #081022;
      color: var(--text);
      border: 1px solid rgba(125,211,252,.18);
      border-radius: 10px;
      padding: 10px 12px;
      font: inherit;
    }}
    textarea {{ min-height: 420px; font-family: ui-monospace, monospace; }}
    button {{
      background: var(--accent);
      color: #081022;
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      font-weight: 700;
      cursor: pointer;
    }}
    button.danger {{ background: var(--danger); }}
    button.secondary {{ background: #263252; color: var(--text); }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(125, 211, 252, 0.12);
      color: var(--text);
      font-size: 0.9rem;
    }}
    .ok {{ color: var(--ok); }}
    .two-col {{ display: grid; gap: 12px; grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #081022; padding: 12px; border-radius: 12px; overflow-x: auto; }}
    details {{ border: 1px solid rgba(125,211,252,.12); border-radius: 12px; padding: 10px 12px; background: rgba(8,16,34,.72); }}
    summary {{ cursor: pointer; font-weight: 700; }}
    .item {{ padding: 10px 0; border-top: 1px solid rgba(125,211,252,.1); }}
    .item:first-child {{ border-top: 0; padding-top: 0; }}
    .kv {{ display: grid; gap: 6px; grid-template-columns: 160px 1fr; align-items: center; }}
  </style>
</head>
<body>
  <main>
    <h1>Network Radio Server</h1>
    <p class="muted">Manifest editor, live status, validation, and apply controls.</p>
    <div class="row" style="margin-bottom: 16px;">
      <button onclick="refreshAll()">Refresh</button>
      <button onclick="saveManifest()">Save Manifest</button>
      <button onclick="renderConfig()">Render Config</button>
      <button class="danger" onclick="applyConfig()">Apply / Restart</button>
    </div>
    <div id="validation" class="card" style="margin-bottom: 16px; display:none;"></div>
    <div class="grid">
      <section class="card">
        <h2>Editor</h2>
        <div class="row" style="margin-bottom: 10px;">
          <span class="pill">Structured sections</span>
          <span class="pill">Raw YAML fallback</span>
        </div>
        <div class="stack">
        <details open>
            <summary>Meta and defaults</summary>
            <div class="two-col" style="margin-top: 12px;">
              <div>
                <label>Install root</label>
                <input id="default-install-root" />
              </div>
              <div>
                <label>Avahi service name</label>
                <input id="avahi-service-name" />
              </div>
              <div>
                <label>Avahi display name</label>
                <input id="avahi-display-name" />
              </div>
              <div>
                <label>Avahi description</label>
                <input id="avahi-description" />
              </div>
            </div>
          </details>
          <details open>
            <summary>Audio streamers</summary>
            <div id="streamers"></div>
          </details>
          <details open>
            <summary>Serial ports</summary>
            <div id="ser2net"></div>
          </details>
          <details open>
            <summary>USB/IP devices</summary>
            <div id="usbip-devices"></div>
          </details>
          <details open>
            <summary>Service enables</summary>
            <div id="services"></div>
          </details>
          <details>
            <summary>Raw manifest preview</summary>
            <textarea id="manifest" readonly>loading…</textarea>
            <p class="muted">The structured form is the primary editor. This preview shows the manifest that will be saved.</p>
          </details>
        </div>
      </section>
      <section class="card">
        <h2>Status</h2>
        <pre id="status">loading…</pre>
      </section>
      <section class="card">
        <h2>Apply Output</h2>
        <pre id="apply">idle</pre>
      </section>
    </div>
  </main>
  <script>
    const emptyManifest = {{ version: 1, defaults: {{}}, avahi: {{}}, services: {{}}, ser2net: [], usbip: {{}}, audio: {{ bridge: {{}}, streamers: [], transports: [] }}, systemd: {{}}, dropins: {{}}, rules: {{}} }};
    let currentManifest = null;

    async function fetchJSON(path, options) {{
      const res = await fetch(path, options);
      const text = await res.text();
      let data;
      try {{ data = JSON.parse(text); }} catch (err) {{ data = {{ ok: false, raw: text }}; }}
      if (!res.ok) throw data;
      return data;
    }}

    function getManifest() {{
      try {{
        return JSON.parse(window.__manifest_json || "null") || emptyManifest;
      }} catch (e) {{
        return emptyManifest;
      }}
    }}

    function renderStreamerRow(streamer, idx) {{
      return `
        <div class="item">
          <div class="two-col">
            <div><label>Name</label><input data-streamer-field="name" data-index="${{idx}}" value="${{streamer.name || ""}}"></div>
            <div><label>Enabled</label><input data-streamer-field="enabled" data-index="${{idx}}" value="${{streamer.enabled !== false}}"></div>
            <div><label>Mode</label><input data-streamer-field="mode" data-index="${{idx}}" value="${{streamer.mode || ""}}"></div>
            <div><label>Logger tag</label><input data-streamer-field="logger_tag" data-index="${{idx}}" value="${{streamer.logger_tag || ""}}"></div>
            <div><label>Source</label><input data-streamer-field="source" data-index="${{idx}}" value="${{streamer.source || ""}}"></div>
            <div><label>Target</label><input data-streamer-field="target" data-index="${{idx}}" value="${{streamer.target || ""}}"></div>
            <div><label>Exec start</label><input data-streamer-field="exec_start" data-index="${{idx}}" value="${{streamer.exec_start || ""}}"></div>
          </div>
        </div>`;
    }}

    function renderSer2netRow(row, idx) {{
      return `
        <div class="item">
          <div class="two-col">
            <div><label>Port</label><input data-ser2net-field="port" data-index="${{idx}}" value="${{row.port ?? ""}}"></div>
            <div><label>Device</label><input data-ser2net-field="device" data-index="${{idx}}" value="${{row.device || ""}}"></div>
            <div><label>Baud</label><input data-ser2net-field="baud" data-index="${{idx}}" value="${{row.baud ?? ""}}"></div>
            <div><label>Format</label><input data-ser2net-field="format" data-index="${{idx}}" value="${{row.format || ""}}"></div>
            <div><label>Flow</label><input data-ser2net-field="flow" data-index="${{idx}}" value="${{row.flow || ""}}"></div>
            <div><label>Notes</label><input data-ser2net-field="notes" data-index="${{idx}}" value="${{row.notes || ""}}"></div>
          </div>
        </div>`;
    }}

    function renderUsbipRow(device, idx) {{
      return `
        <div class="item">
          <div class="two-col">
            <div><label>Bus ID</label><input data-usbip-field="busid" data-index="${{idx}}" value="${{device.busid || ""}}"></div>
            <div><label>Name</label><input data-usbip-field="name" data-index="${{idx}}" value="${{device.name || ""}}"></div>
            <div><label>Enabled</label><input data-usbip-field="enabled" data-index="${{idx}}" value="${{device.enabled !== false}}"></div>
          </div>
        </div>`;
    }}

    function renderServiceRow(name, enabled) {{
      return `
        <div class="item kv">
          <label>${{name}}</label>
          <input data-service-name="${{name}}" value="${{enabled ? "true" : "false"}}">
        </div>`;
    }}

    function populateForm(manifest) {{
      currentManifest = manifest;
      window.__manifest_json = JSON.stringify(manifest);
      document.getElementById("manifest").value = document.getElementById("manifest").value || JSON.stringify(manifest, null, 2);
      document.getElementById("default-install-root").value = manifest.defaults?.install_root || "";
      document.getElementById("avahi-service-name").value = manifest.avahi?.service_name || "";
      document.getElementById("avahi-display-name").value = manifest.avahi?.display_name || "";
      document.getElementById("avahi-description").value = manifest.avahi?.description || "";
      const streamers = manifest.audio?.streamers || [];
      document.getElementById("streamers").innerHTML = streamers.map(renderStreamerRow).join("") || '<div class="muted">No streamers defined.</div>';
      document.getElementById("ser2net").innerHTML = (manifest.ser2net || []).map(renderSer2netRow).join("") || '<div class="muted">No serial ports defined.</div>';
      document.getElementById("usbip-devices").innerHTML = (manifest.usbip?.devices || []).map(renderUsbipRow).join("") || '<div class="muted">No USB/IP devices defined.</div>';
      document.getElementById("services").innerHTML = Object.entries(manifest.services || {{}}).map(function(entry) {{ const name = entry[0]; const enabled = entry[1]; return renderServiceRow(name, enabled); }}).join("") || '<div class="muted">No services defined.</div>';
    }}

    function collectManifest() {{
      const manifest = JSON.parse(JSON.stringify(currentManifest || emptyManifest));
      manifest.defaults = manifest.defaults || {{}};
      manifest.avahi = manifest.avahi || {{}};
      manifest.audio = manifest.audio || {{}};
      manifest.usbip = manifest.usbip || {{}};
      manifest.services = manifest.services || {{}};
      manifest.audio.streamers = manifest.audio.streamers || [];
      manifest.ser2net = manifest.ser2net || [];
      manifest.usbip.devices = manifest.usbip.devices || [];
      manifest.defaults.install_root = document.getElementById("default-install-root").value.trim() || manifest.defaults.install_root;
      manifest.avahi.service_name = document.getElementById("avahi-service-name").value.trim() || manifest.avahi.service_name;
      manifest.avahi.display_name = document.getElementById("avahi-display-name").value.trim() || manifest.avahi.display_name;
      manifest.avahi.description = document.getElementById("avahi-description").value.trim() || manifest.avahi.description;
      document.querySelectorAll("[data-streamer-field]").forEach((node) => {{
        const idx = Number(node.dataset.index);
        const field = node.dataset.streamerField;
        if (!manifest.audio.streamers[idx]) return;
        if (field === "enabled") {{
          manifest.audio.streamers[idx][field] = node.value !== "false";
        }} else {{
          manifest.audio.streamers[idx][field] = node.value;
        }}
      }});
      document.querySelectorAll("[data-ser2net-field]").forEach((node) => {{
        const idx = Number(node.dataset.index);
        const field = node.dataset.ser2netField;
        if (!manifest.ser2net[idx]) return;
        manifest.ser2net[idx][field] = field === "baud" || field === "port" ? Number(node.value) || node.value : node.value;
      }});
      document.querySelectorAll("[data-usbip-field]").forEach((node) => {{
        const idx = Number(node.dataset.index);
        const field = node.dataset.usbipField;
        if (!manifest.usbip.devices[idx]) return;
        if (field === "enabled") {{
          manifest.usbip.devices[idx][field] = node.value !== "false";
        }} else {{
          manifest.usbip.devices[idx][field] = node.value;
        }}
      }});
      document.querySelectorAll("[data-service-name]").forEach((node) => {{
        manifest.services[node.dataset.serviceName] = node.value !== "false";
      }});
      return manifest;
    }}

    function showValidation(errors) {{
      const box = document.getElementById("validation");
      if (!errors || !errors.length) {{
        box.style.display = "none";
        box.innerHTML = "";
        return;
      }}
      box.style.display = "block";
      box.innerHTML = `<h2>Validation errors</h2><ul>${{errors.map((e) => `<li>${{e}}</li>`).join("")}}</ul>`;
    }}

    async function refreshAll() {{
      const raw = await (await fetch("/api/manifest")).text();
      document.getElementById("manifest").value = raw;
      const parsed = JSON.parse(raw);
      populateForm(parsed);
      document.getElementById("status").textContent = JSON.stringify(await fetchJSON("/api/status"), null, 2);
      const validations = await fetchJSON("/api/validate");
      showValidation(validations.errors || []);
    }}

    async function saveManifest() {{
      document.getElementById("apply").textContent = "Saving manifest…";
      const structured = collectManifest();
      const body = JSON.stringify(structured, null, 2);
      const result = await fetchJSON("/api/manifest", {{
        method: "POST",
        headers: {{ "Content-Type": "text/yaml; charset=utf-8" }},
        body,
      }});
      document.getElementById("apply").textContent = JSON.stringify(result, null, 2);
      await refreshAll();
    }}

    async function renderConfig() {{
      document.getElementById("apply").textContent = "Rendering…";
      document.getElementById("apply").textContent = JSON.stringify(await fetchJSON("/api/render", {{ method: "POST" }}), null, 2);
      await refreshAll();
    }}

    async function applyConfig() {{
      document.getElementById("apply").textContent = "Applying…";
      document.getElementById("apply").textContent = JSON.stringify(await fetchJSON("/api/apply", {{ method: "POST" }}), null, 2);
      await refreshAll();
    }}

    refreshAll().catch(err => {{
      document.getElementById("status").textContent = JSON.stringify(err, null, 2);
    }});
  </script>
</body>
</html>
""".encode("utf-8")


def render_config() -> dict:
    if not RENDERER.exists():
        return {"ok": False, "error": "renderer not found", "path": str(RENDERER)}
    return run_capture([str(RENDERER)])


def apply_config() -> dict:
    if not DEPLOY.exists():
        return {"ok": False, "error": "deploy script not found", "path": str(DEPLOY)}
    return run_capture(["bash", str(DEPLOY)])


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: object) -> None:
        body = json.dumps(payload, indent=2, sort_keys=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, code: int, body: str) -> None:
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            body = dashboard_page()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/status":
            self._json(200, build_status())
            return
        if parsed.path == "/api/manifest":
            self._text(200, canonical_yaml(load_yaml(MANIFEST)))
            return
        if parsed.path == "/api/validate":
            manifest = load_yaml(MANIFEST)
            self._json(200, {"ok": not validation_errors(manifest), "errors": validation_errors(manifest)})
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/manifest":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            try:
                manifest = yaml.safe_load(raw)
                if not isinstance(manifest, dict):
                    raise ValueError("manifest must be a mapping")
                errors = validation_errors(manifest)
                if errors:
                    self._json(400, {"ok": False, "errors": errors})
                    return
                MANIFEST.write_text(canonical_yaml(manifest), encoding="utf-8")
            except Exception as exc:
                self._json(400, {"ok": False, "error": str(exc)})
                return
            self._json(200, {"ok": True, "manifest_path": str(MANIFEST), "revision": file_hash(MANIFEST), "valid": True})
            return
        if parsed.path == "/api/render":
            self._json(200, render_config())
            return
        if parsed.path == "/api/apply":
            self._json(200, apply_config())
            return
        self._json(404, {"ok": False, "error": "not found"})


def main() -> None:
    port = int(os.environ.get("PORT", "8787"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Network Radio Dashboard listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
