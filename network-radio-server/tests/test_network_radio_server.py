from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for network-radio-server tests") from exc


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config.yaml"
RENDERER = ROOT / "render-config.py"
DEPLOY = ROOT / "deploy.sh"
TARGET = ROOT / "generated" / "systemd" / "network-radio-server.target"


class NetworkRadioServerTests(unittest.TestCase):
    def test_manifest_loads_and_has_required_shape(self) -> None:
        with MANIFEST.open("r", encoding="utf-8") as fh:
            manifest = yaml.safe_load(fh)

        self.assertIsInstance(manifest, dict)
        for key in ("version", "defaults", "ser2net", "usbip", "audio", "systemd", "avahi", "services", "dropins", "rules"):
            self.assertIn(key, manifest)

        self.assertEqual(manifest["services"].get("network_radio_server_target"), True)

    def test_renderer_emits_target_enable_flag(self) -> None:
        text = RENDERER.read_text(encoding="utf-8")
        self.assertIn("ENABLE_NETWORK_RADIO_SERVER_TARGET", text)

    def test_deploy_enables_target(self) -> None:
        text = DEPLOY.read_text(encoding="utf-8")
        self.assertIn("ENABLE_NETWORK_RADIO_SERVER_TARGET", text)
        self.assertIn("network-radio-server.target", text)

    def test_target_file_wires_stack(self) -> None:
        text = TARGET.read_text(encoding="utf-8")
        self.assertIn("usbipd.service", text)
        self.assertIn("usbip-bind.service", text)
        self.assertIn("usbip-attach.service", text)
        self.assertIn("usbip-watchdog.service", text)
        self.assertIn("ser2net.service", text)
        self.assertIn("radio-audio.service", text)
        self.assertIn("radio-audio-streamer.service", text)
        self.assertIn("network-radio-dashboard.service", text)

    def test_target_unit_name_is_valid(self) -> None:
        self.assertTrue(re.fullmatch(r"[a-z0-9-]+\.target", TARGET.name))

    def test_renderer_rebuilds_generated_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shutil.copy2(RENDERER, tmp / "render-config.py")
            shutil.copy2(MANIFEST, tmp / "config.yaml")

            for rel in ("generated/systemd", "generated/dropins", "generated/rules", "ser2net", "usbip", "avahi"):
                (tmp / rel).mkdir(parents=True, exist_ok=True)

            subprocess.run(["python3", "render-config.py"], cwd=tmp, check=True)

            generated_env = (tmp / "generated.env").read_text(encoding="utf-8")
            self.assertIn("ENABLE_NETWORK_RADIO_SERVER_TARGET=true", generated_env)
            self.assertIn("ENABLE_USBIPD=true", generated_env)

            target = (tmp / "generated/systemd/network-radio-server.target").read_text(encoding="utf-8")
            self.assertIn("Wants=usbipd.service usbip-bind.service usbip-attach.service usbip-watchdog.service ser2net.service radio-audio.service radio-audio-streamer.service network-radio-dashboard.service", target)
            self.assertIn("WantedBy=multi-user.target", target)

            manifest = yaml.safe_load((tmp / "config.yaml").read_text(encoding="utf-8"))
            self.assertIsInstance(manifest, dict)
            self.assertEqual(manifest["services"].get("network_radio_server_target"), True)


if __name__ == "__main__":
    unittest.main()
