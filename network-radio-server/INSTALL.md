# Network Radio Server Install

This bundle is installed from a single manifest:

- `config.yaml` is the source of truth.
- `render-config.py` generates all deploy-time artifacts.
- `deploy.sh` installs the generated files and enables the services selected in
  the manifest.

## Debian 13

The expected path on Debian 13 is:

1. Clone or fetch the repo.
2. Review `config.yaml`.
3. Install dependencies:
   - `sudo ./install-deps.sh`
4. Deploy:
   - `sudo ./deploy.sh`

If you want the dashboard to manage edits instead of hand-editing the manifest,
start the dashboard service after deployment and use its structured editor to
save changes, validate them, and re-run render/apply.

If the host is missing Python YAML support, install `python3-yaml` first.
The dependency installer is distro-aware, so this is the place to add support
for new Linux families later.

## Bootstrap

For a fresh machine, use `bootstrap-install.sh`:

```bash
sudo ./bootstrap-install.sh
```

That script clones the AF4H repo, sparsely checks out
`network-radio-server`, installs minimal bootstrap tooling first, then
installs dependencies, and runs deployment.
Run it as root, typically via `sudo`, because it installs packages before the
repo exists locally.

If you already have the repo, you can skip bootstrap and run:

```bash
sudo ./install-deps.sh
sudo ./deploy.sh
```

## Build Initial Configuration

After bootstrapping, the initial configuration flow is:

1. Edit `config.yaml` for the target host.
2. Run `sudo ./render-config.py` if you want to inspect the generated outputs.
3. Run `sudo ./deploy.sh` to install the generated config and enable the
   selected services.

The dashboard can also edit the common manifest sections, validate them, and
then save, render, and apply through the same flow.

## Browser Workflow

If the dashboard is running, you can manage the initial config from a browser:

1. Start the service if needed:
   ```bash
   sudo systemctl start network-radio-dashboard
   ```
2. Find the host IP:
   ```bash
   hostname -I
   ```
3. Open `http://HOST_IP:8787/`.
4. Edit the structured manifest sections.
5. Click `Save Manifest`, then `Render Config`, then `Apply / Restart`.

If you prefer an SSH tunnel instead of exposing the port directly:

```bash
ssh -L 8787:localhost:8787 user@HOST
```

Then open `http://localhost:8787/`.

## Partial Checkout

`bootstrap-install.sh` already does a sparse checkout of just the
`network-radio-server` tree, so you do not need to clone the full repository
for installs or upgrades.

## Upgrade Path

1. Pull the latest repo changes.
2. Reconcile `config.yaml` with any new options.
3. Re-run `./deploy.sh`.
4. Restart or reload the affected services if you changed runtime behavior.

Because the generated systemd units, rules, drop-ins, and config files all come
from `config.yaml`, upgrades should mostly be a matter of updating the manifest
and redeploying.
If you change only data in the manifest, rerunning `deploy.sh` is enough to
regenerate and reapply the affected outputs.

## Distro Support

The dependency installer is intentionally split by distro. Adding a new distro
means teaching `install-deps.sh` how to install the required packages for that
platform.
