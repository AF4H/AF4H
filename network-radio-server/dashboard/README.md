# Dashboard

The dashboard is a lightweight operator surface for `network-radio-server`.
It now serves:

- `GET /` - a small status page with a structured manifest editor
- `GET /api/manifest` - the canonical manifest text from `config.yaml`
- `POST /api/manifest` - save edited manifest data back to `config.yaml`
- `GET /api/status` - live service and host status
- `GET /api/validate` - validate the current manifest
- `POST /api/render` - rerender generated artifacts from `config.yaml`
- `POST /api/apply` - rerender and apply the install/deploy path

The dashboard is intentionally thin. It is not a second config system.
Anything editable lands in `config.yaml`, then gets rendered and applied
through the same deployment path used by `deploy.sh`.

The current editor is intentionally split:

- structured inputs for the common fields
- a raw manifest preview for review
- validation feedback before writes are accepted
- discovery helpers that can import serial, audio, and USB/IP candidates into
  the manifest for review before saving

Status includes:

- `systemctl` service state
- USB/IP configuration inventory
- serial port inventory
- audio bridge and streamer inventory
- host identity and network reachability
- manifest revision and last render time

That keeps the eventual web UI honest: the UI can read the manifest, show live
status, validate edits, and invoke the same render/apply flow that a shell
operator would use.
