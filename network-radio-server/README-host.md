# Network Radio Server Host

This is the installed host-side bundle for `network-radio-server`.

## Live Files

- `/opt/network-radio-server/generated.env`
- `/opt/network-radio-server/config.yaml`
- `/opt/network-radio-server/deploy.sh`
- `/opt/network-radio-server/render-config.py`
- `/opt/network-radio-server/bootstrap-install.sh`
- `/opt/network-radio-server/install-deps.sh`

## Common Actions

Reapply the current manifest and regenerate outputs:

```bash
sudo /opt/network-radio-server/deploy.sh
```

Regenerate outputs only:

```bash
sudo /opt/network-radio-server/render-config.py
```

Bootstrap a fresh host from the installed scripts:

```bash
sudo /opt/network-radio-server/bootstrap-install.sh
```

Start the whole stack in one shot:

```bash
sudo systemctl start network-radio-server.target
```

## Suggested Startup Order

After a fresh deploy, bring the stack up in this order:

1. `usbipd`
2. `usbip-bind`
3. `usbip-attach`
4. `usbip-watchdog`
5. `ser2net`
6. `radio-audio`
7. `radio-audio-streamer`
8. `network-radio-dashboard`

For a quick check:

```bash
systemctl status usbipd usbip-bind usbip-attach usbip-watchdog ser2net \
  radio-audio radio-audio-streamer network-radio-dashboard --no-pager -l
```

If the dashboard does not respond, check:

- `systemctl status network-radio-dashboard --no-pager -l`
- `ss -ltnp | grep 8787`
- `/opt/network-radio-server/generated.env`

## Dashboard

If the dashboard service is enabled, open:

```text
http://HOST_IP:8787/
```

Or use an SSH tunnel:

```bash
ssh -L 8787:localhost:8787 user@HOST
```

Then open `http://localhost:8787/`.
