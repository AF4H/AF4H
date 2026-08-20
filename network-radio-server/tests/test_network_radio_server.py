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
        self.assertIn('install_tree "$ROOT_DIR/avahi" "$INSTALL_ROOT/avahi"', text)
        self.assertIn('install_dir "$ROOT_DIR/ser2net/ser2net.conf.example" "$SER2NET_CONF"', text)
        self.assertIn("same_path()", text)
        self.assertIn('left="$(readlink -f "$1")"', text)

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
            self.assertIn("AUDIO_STREAMER_ENABLED=true", generated_env)
            self.assertIn("AUDIO_STREAMER_LOGGER_TAG=WWH23-feed", generated_env)
            self.assertIn("SAME_ENABLED=true", generated_env)
            self.assertIn("SAME_WATCH_TAG=same-watch", generated_env)
            self.assertIn("SAME_ACTION_TAG=same-act", generated_env)

            target = (tmp / "generated/systemd/network-radio-server.target").read_text(encoding="utf-8")
            self.assertIn("Wants=usbipd.service usbip-bind.service usbip-attach.service usbip-watchdog.service ser2net.service radio-audio.service radio-audio-streamer.service network-radio-dashboard.service", target)
            self.assertIn("WantedBy=multi-user.target", target)
            usbipd_unit = (tmp / "generated/systemd/usbipd.service").read_text(encoding="utf-8")
            self.assertIn("ExecStart=/usr/sbin/usbipd -D -P /run/usbipd.pid", usbipd_unit)
            self.assertNotIn("PIDFile=/run/usbipd.pid", usbipd_unit)
            self.assertTrue((tmp / "ser2net" / "ser2net.conf.example").exists())
            self.assertTrue((tmp / "avahi" / "radio-server.service").exists())

            manifest = yaml.safe_load((tmp / "config.yaml").read_text(encoding="utf-8"))
            self.assertIsInstance(manifest, dict)
            self.assertEqual(manifest["services"].get("network_radio_server_target"), True)

    def test_discovery_helpers_see_serial_audio_and_usb(self) -> None:
        def fake_run_lines(cmd: list[str]) -> list[str]:
            joined = " ".join(cmd)
            if "asound/cards" in joined:
                return ["0|USB Audio Adapter"]
            if cmd == ["usbip", "list", "-l"]:
                return [" - 1-1.2.4.1: AF4H USB Sound Adapter"]
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
        self.assertEqual(usb[0]["busid"], "1-1.2.4.1")
        self.assertEqual(usb[0]["label"], "AF4H USB Sound Adapter")
        self.assertEqual(usb[0]["name"], "AF4H USB Sound Adapter")
        self.assertEqual(usb[0]["description"], " - 1-1.2.4.1: AF4H USB Sound Adapter")

    def test_dashboard_includes_quick_wizard(self) -> None:
        text = (ROOT / "dashboard" / "server.py").read_text(encoding="utf-8")
        self.assertIn("runQuickWizard()", text)
        self.assertIn("Quick Wizard", text)
        self.assertIn("wizard-status", text)
        self.assertIn("data-discovery-usbip-include", text)
        self.assertIn("addDiscoveredUsbip", text)
        self.assertIn("importAllUsbip", text)
        self.assertIn("renderDiscoveryUsbip", text)

    def test_usbip_scripts_validate_config_and_use_literal_busid_match(self) -> None:
        attach = (ROOT / "usbip" / "client" / "usbip-attach.sh").read_text(encoding="utf-8")
        watchdog = (ROOT / "usbip" / "client" / "usbip-watchdog.sh").read_text(encoding="utf-8")
        bind = (ROOT / "usbip" / "usbip-bind.sh").read_text(encoding="utf-8")

        self.assertIn('CONFIG_FILE="${USBIP_CONFIG:-/etc/usbip/devices.conf}"', attach)
        self.assertIn('CONFIG_FILE="${USBIP_CONFIG:-/etc/usbip/devices.conf}"', watchdog)
        self.assertIn('PATH=/usr/sbin:/usr/bin:/sbin:/bin usbip list -r "$SERVER"', attach)
        self.assertIn('skipped $BUSID; not present on $SERVER', attach)
        self.assertIn('PATH=/usr/sbin:/usr/bin:/sbin:/bin usbip attach -r "$SERVER" -b "$BUSID" || true', attach)
        self.assertIn('PATH=/usr/sbin:/usr/bin:/sbin:/bin usbip list -r "$SERVER"', watchdog)
        self.assertIn('usbip bind -b "$busid" || true', bind)
        self.assertIn('grep -Fq "$busid"', bind)
        self.assertIn('missing SERVER in $CONFIG_FILE', attach)
        self.assertIn('missing SERVER in $CONFIG_FILE', watchdog)

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
