# Network Radio Server Host

This is the installed host-side bundle for `network-radio-server`.

## Live Files

- `/opt/network-radio-server/generated.env`
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
