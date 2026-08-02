# Network Radio Server Upgrade Path

Use the same manifest-driven flow for upgrades:

1. Update the repo.
2. Edit `config.yaml` if new hardware or services were added.
3. Run `./render-config.py` or just `./deploy.sh` to refresh generated files.
4. Re-run `./deploy.sh`.
5. Restart the affected services.

If the manifest only changed data that feeds generated files, `deploy.sh` is
usually enough because it regenerates and installs the outputs.
If the manifest changes service enable flags, `deploy.sh` will also update the
enabled units to match.

If you are using the dashboard, the normal path is:

1. Edit the structured manifest fields.
2. Let the dashboard validate the manifest.
3. Save, render, and apply from the same UI.

If you change the helper scripts themselves, redeploy and restart the affected
services afterward.
