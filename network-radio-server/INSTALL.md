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
sudo ./bootstrap-install.sh <repo-url> [ref]
```

That script clones the repo, checks out the requested ref, installs
minimal bootstrap tooling first, then installs dependencies, and runs
deployment.

If you already have the repo, you can skip bootstrap and run:

```bash
sudo ./install-deps.sh
sudo ./deploy.sh
```

## Partial Checkout

Yes. If you only want `network-radio-server`, you do not need to clone the
entire repository. Use Git sparse checkout:

```bash
git clone --filter=blob:none --sparse https://github.com/AF4H/AF4H.git
cd AF4H
git sparse-checkout set network-radio-server
```

That gives you just the tree you need while still keeping normal Git history
available for that path. If you only want the current files and do not care
about Git operations afterward, you can also download the GitHub subtree as a
ZIP from the `network-radio-server` directory view, but sparse checkout is the
better option for install and upgrade workflows.

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
