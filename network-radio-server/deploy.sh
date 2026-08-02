#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/network-radio-server}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
AVAHI_SERVICES_DIR="${AVAHI_SERVICES_DIR:-/etc/avahi/services}"
UDEV_RULES_DIR="${UDEV_RULES_DIR:-/etc/udev/rules.d}"
SER2NET_CONF="${SER2NET_CONF:-/etc/ser2net.conf}"
USBIP_CONF="${USBIP_CONF:-/etc/usbip/devices.conf}"
CONFIG_RENDERER="${CONFIG_RENDERER:-$ROOT_DIR/render-config.py}"
LOCAL_BIN_DIR="${LOCAL_BIN_DIR:-/usr/local/bin}"

install_dir() {
  local src="$1"
  local dst="$2"
  install -d "$(dirname "$dst")"
  install -m 0644 "$src" "$dst"
}

install_tree() {
  local src_dir="$1"
  local dst_dir="$2"
  install -d "$dst_dir"
  cp -a "$src_dir/." "$dst_dir/"
}

echo "Installing network-radio-server bundle to ${INSTALL_ROOT}"

install -d "$INSTALL_ROOT"
install_tree "$ROOT_DIR/audio" "$INSTALL_ROOT/audio"
install_tree "$ROOT_DIR/audio/streamer" "$INSTALL_ROOT/audio/streamer"
install_tree "$ROOT_DIR/dashboard" "$INSTALL_ROOT/dashboard"
install_tree "$ROOT_DIR/ser2net" "$INSTALL_ROOT/ser2net"
install_tree "$ROOT_DIR/usbip" "$INSTALL_ROOT/usbip"

if [[ ! -x "$CONFIG_RENDERER" ]]; then
  echo "missing config renderer: $CONFIG_RENDERER" >&2
  exit 1
fi

install -d "$(dirname "$SER2NET_CONF")" "$(dirname "$USBIP_CONF")"

"$CONFIG_RENDERER"
source "$ROOT_DIR/generated.env"

install_dir "$ROOT_DIR/systemd/usbip-bind.service.d/override.conf" \
  "$SYSTEMD_DIR/usbip-bind.service.d/override.conf"
install_dir "$ROOT_DIR/systemd/ser2net.service" "$SYSTEMD_DIR/ser2net.service"
install_dir "$ROOT_DIR/systemd/radio-audio.service" "$SYSTEMD_DIR/radio-audio.service"
install_dir "$ROOT_DIR/systemd/network-radio-dashboard.service" "$SYSTEMD_DIR/network-radio-dashboard.service"
install_dir "$ROOT_DIR/systemd/radio-audio-streamer.service" "$SYSTEMD_DIR/radio-audio-streamer.service"
install_dir "$ROOT_DIR/usbip/server/usbipd.service" "$SYSTEMD_DIR/usbipd.service"
install_dir "$ROOT_DIR/usbip/server/usbip-bind.service" "$SYSTEMD_DIR/usbip-bind.service"
install_dir "$ROOT_DIR/usbip/client/usbip-attach.service" "$SYSTEMD_DIR/usbip-attach.service"
install_dir "$ROOT_DIR/usbip/client/usbip-watchdog.service" "$SYSTEMD_DIR/usbip-watchdog.service"
install_dir "$ROOT_DIR/systemd/avahi-daemon.service.d/override.conf" \
  "$SYSTEMD_DIR/avahi-daemon.service.d/override.conf"
install_dir "$ROOT_DIR/avahi/radio-pi.service" "$AVAHI_SERVICES_DIR/radio-pi.service"
install_dir "$ROOT_DIR/udev/usbip-bind.rules" "$UDEV_RULES_DIR/99-network-radio-server-usbip.rules"
install_dir "$ROOT_DIR/usbip/server/99-usbip-autobind.rules" "$UDEV_RULES_DIR/99-usbip-autobind.rules"

install -d "$LOCAL_BIN_DIR"
install -m 0755 "$ROOT_DIR/audio/radio-audio-bridge.sh" "$INSTALL_ROOT/audio/radio-audio-bridge.sh"
install -m 0755 "$ROOT_DIR/audio/streamer/WWH23-feed.sh" "$INSTALL_ROOT/audio/streamer/WWH23-feed.sh"
install -m 0755 "$ROOT_DIR/audio/streamer/same-act.sh" "$INSTALL_ROOT/audio/streamer/same-act.sh"
install -m 0755 "$ROOT_DIR/audio/streamer/same-watch.sh" "$INSTALL_ROOT/audio/streamer/same-watch.sh"
install -m 0755 "$ROOT_DIR/usbip/usbip-bind.sh" "$LOCAL_BIN_DIR/usbip-bind.sh"
install -m 0755 "$ROOT_DIR/usbip/client/usbip-attach.sh" "$LOCAL_BIN_DIR/usbip-attach.sh"
install -m 0755 "$ROOT_DIR/usbip/client/usbip-watchdog.sh" "$LOCAL_BIN_DIR/usbip-watchdog.sh"
install -m 0644 "$ROOT_DIR/usbip/devices.conf.example" "$USBIP_CONF"
systemctl daemon-reload
udevadm control --reload-rules || true
services_to_enable=()
[[ "${ENABLE_USBIPD}" == "true" ]] && services_to_enable+=(usbipd.service)
[[ "${ENABLE_USBIP_BIND}" == "true" ]] && services_to_enable+=(usbip-bind.service)
[[ "${ENABLE_USBIP_ATTACH}" == "true" ]] && services_to_enable+=(usbip-attach.service)
[[ "${ENABLE_USBIP_WATCHDOG}" == "true" ]] && services_to_enable+=(usbip-watchdog.service)
[[ "${ENABLE_SER2NET}" == "true" ]] && services_to_enable+=(ser2net.service)
[[ "${ENABLE_RADIO_AUDIO}" == "true" ]] && services_to_enable+=(radio-audio.service)
[[ "${ENABLE_RADIO_AUDIO_STREAMER}" == "true" ]] && services_to_enable+=(radio-audio-streamer.service)
[[ "${ENABLE_NETWORK_RADIO_DASHBOARD}" == "true" ]] && services_to_enable+=(network-radio-dashboard.service)
if ((${#services_to_enable[@]})); then
  systemctl enable "${services_to_enable[@]}"
fi

echo "Installed systemd units and config files."
echo "Review /etc/ser2net.conf and /etc/usbip/devices.conf before starting services."
