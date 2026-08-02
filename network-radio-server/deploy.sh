#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/network-radio-server}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
AVAHI_SERVICES_DIR="${AVAHI_SERVICES_DIR:-/etc/avahi/services}"
UDEV_RULES_DIR="${UDEV_RULES_DIR:-/etc/udev/rules.d}"
SER2NET_CONF="${SER2NET_CONF:-/etc/ser2net.conf}"
USBIP_CONF="${USBIP_CONF:-/etc/usbip/devices.conf}"
SER2NET_RENDERER="${SER2NET_RENDERER:-$ROOT_DIR/ser2net/render-ser2net.sh}"
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

install -d "$(dirname "$SER2NET_CONF")" "$(dirname "$USBIP_CONF")"
if [[ ! -x "$SER2NET_RENDERER" ]]; then
  echo "missing ser2net renderer: $SER2NET_RENDERER" >&2
  exit 1
fi
if ! awk -F'\t' '
  NR == 1 { next }
  NF < 4 {
    printf "invalid ser2net row at line %d\n", NR > "/dev/stderr"
    exit 1
  }
  {
    if ($1 == "" || $2 == "" || $3 == "" || $4 == "") {
      printf "missing required ser2net field at line %d\n", NR > "/dev/stderr"
      exit 1
    }
    if (seen[$1]++) {
      printf "duplicate ser2net port: %s\n", $1 > "/dev/stderr"
      exit 1
    }
  }
' "$ROOT_DIR/ser2net/port-map.tsv"; then
  exit 1
fi
"$SER2NET_RENDERER" "$ROOT_DIR/ser2net/port-map.tsv" > "$SER2NET_CONF"
install -d "$LOCAL_BIN_DIR"
install -m 0755 "$ROOT_DIR/audio/radio-audio-bridge.sh" "$INSTALL_ROOT/audio/radio-audio-bridge.sh"
install -m 0755 "$ROOT_DIR/audio/streamer/WWH23-feed.sh" "$INSTALL_ROOT/audio/streamer/WWH23-feed.sh"
install -m 0755 "$ROOT_DIR/audio/streamer/same-act.sh" "$INSTALL_ROOT/audio/streamer/same-act.sh"
install -m 0755 "$ROOT_DIR/audio/streamer/same-watch.sh" "$INSTALL_ROOT/audio/streamer/same-watch.sh"
install -m 0755 "$ROOT_DIR/usbip/usbip-bind.sh" "$LOCAL_BIN_DIR/usbip-bind.sh"
install -m 0755 "$ROOT_DIR/usbip/client/usbip-attach.sh" "$LOCAL_BIN_DIR/usbip-attach.sh"
install -m 0755 "$ROOT_DIR/usbip/client/usbip-watchdog.sh" "$LOCAL_BIN_DIR/usbip-watchdog.sh"
install -m 0644 "$ROOT_DIR/usbip/client/etc/usbip/devices.conf" "$USBIP_CONF"
install -m 0755 "$ROOT_DIR/ser2net/render-ser2net.sh" "$INSTALL_ROOT/ser2net/render-ser2net.sh"
systemctl daemon-reload
udevadm control --reload-rules || true
systemctl enable usbipd.service usbip-bind.service ser2net.service radio-audio.service network-radio-dashboard.service

echo "Installed systemd units and config files."
echo "Review /etc/ser2net.conf and /etc/usbip/devices.conf before starting services."
