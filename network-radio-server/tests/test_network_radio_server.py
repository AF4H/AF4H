from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        self.assertIn("AUDIO_ADAPTER_COUNT", text)

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
            self.assertIn("AUDIO_ADAPTER_COUNT=0", generated_env)

            target = (tmp / "generated/systemd/network-radio-server.target").read_text(encoding="utf-8")
            self.assertIn("Wants=usbipd.service usbip-bind.service usbip-attach.service usbip-watchdog.service ser2net.service radio-audio.service radio-audio-streamer.service network-radio-dashboard.service", target)
            self.assertIn("WantedBy=multi-user.target", target)

            manifest = yaml.safe_load((tmp / "config.yaml").read_text(encoding="utf-8"))
            self.assertIsInstance(manifest, dict)
            self.assertEqual(manifest["services"].get("network_radio_server_target"), True)

    def test_discovery_helpers_see_serial_audio_and_usb(self) -> None:
        def fake_run_lines(cmd: list[str]) -> list[str]:
            joined = " ".join(cmd)
            if "asound/cards" in joined:
                return ["0|USB Audio Adapter"]
            if cmd == ["lsusb"]:
                return ["Bus 001 Device 002: ID 1234:abcd AF4H Radio Adapter"]
            return []

        with mock.patch.object(self.module, "run_lines", side_effect=fake_run_lines), \
             mock.patch.object(self.module.Path, "glob", return_value=[Path("/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_TEST-if00-port0")]), \
             mock.patch.object(self.module.Path, "exists", return_value=True):
            serials = self.module.discover_serial_ports()
            audio = self.module.discover_audio_devices()
            usb = self.module.discover_usbip_devices()

        self.assertEqual(len(serials), 1)
        self.assertEqual(serials[0]["device"], "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_TEST-if00-port0")
        self.assertEqual(serials[0]["baud"], 115200)
        self.assertEqual(audio[0]["card"], 0)
        self.assertEqual(audio[0]["label"], "USB Audio Adapter")
        self.assertEqual(usb[0]["description"], "Bus 001 Device 002: ID 1234:abcd AF4H Radio Adapter")

    def test_dashboard_includes_quick_wizard(self) -> None:
        text = (ROOT / "dashboard" / "server.py").read_text(encoding="utf-8")
        self.assertIn("runQuickWizard()", text)
        self.assertIn("Quick Wizard", text)
        self.assertIn("wizard-status", text)

    @classmethod
    def setUpClass(cls) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("dashboard_server", ROOT / "dashboard" / "server.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.module = module


if __name__ == "__main__":
    unittest.main()
