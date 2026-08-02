# QSL Indexing Scripts

This directory holds the scanner workflow for incoming QSL cards.

## What It Does

- Scans the front and back of a card with a duplex scanner
- Stores the files in dated folders like `2026/04/04/CALLSIGN.front.png`
- Generates a per-card HTML page that shows both sides
- Generates gallery pages with 24 fronts per page
- Builds a top-level index for moving through dates
- Optionally publishes only the files generated in that run to a web server with `rsync`, `scp`, or any other command you prefer

## Files

- `qslindex.py`: Python implementation of the scanner, HTML generator, and publisher
- `qslscan.sh`: thin shell wrapper for the scanner workflow
- `config.ini.example`: sample config with scanner, output, and publish settings

## Setup

1. Copy `config.ini.example` to `config.ini`.
2. Set your scanner device and output root.
3. Set `publish.command` if you want automatic upload after each build.

## Usage

Scan a card:

```bash
./qslscan.sh CALLSIGN 2026-04-04
```

Or use the older style if you are already used to it:

```bash
./qslscan.sh QSL CALLSIGN 2026-04-04
```

Rebuild HTML without scanning:

```bash
python3 qslindex.py build
```

Poke the generator after an upload or sync:

```bash
python3 qslindex.py poke
```

## Notes

- The generated HTML is intentionally plain and dependency-free so it will run cleanly on a fresh Debian install.
- The publish step is intentionally flexible. A simple `rsync` command is the easiest way to upload only the current run's files, but any shell command works if you need FTP or `scp`.
