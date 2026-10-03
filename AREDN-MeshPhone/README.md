# AREDN MeshPhone Route Builder

Builds topology-aware Asterisk MeshPhone dialplan routes from the N2MH MeshPhone administration lists.

## What it does

- Reads the MeshPhone dial-plan and trunk tables from n2mh-web.local.mesh.
- Builds a PBX/trunk graph.
- Finds shortest paths from the local office code to destination office codes.
- Maps configured first-hop office codes to local IAX2 peer names.
- Generates Asterisk routes with runtime failover across enabled peers.
- Discovers local IAX peers and matches them to MeshPhone PBX office codes.
- Reports unmatched peers and mapping conflicts for review.

The web data describes topology; local IAX credentials and peer names remain site-specific and are never generated from public data.

## Files

- routebuilder.py — generates MeshPhone dialplan routes.
- discover_peers.py — matches local IAX peers to PBX office codes.
- refresh.py — runs discovery, preserves manual mappings, rebuilds routes, and reloads Asterisk.
- peers.example.json — example site-specific peer mapping.
- freepbx-module/ — FreePBX MeshPhone Alerts module.
- cron.example — example scheduled refresh entry.

## Configuration

Copy peers.example.json to a private local path and set the local office code and enabled first-hop mappings. The peer names must already exist in the local Asterisk IAX configuration.

Example:

    {
      "local_office": "40423",
      "peers": {
        "93710": { "peer": "nc8q", "enabled": true },
        "97321": { "peer": "n2mh", "enabled": true },
        "13163": { "peer": "w1aw", "enabled": false }
      }
    }

Do not commit local peer files containing operational details.

## Manual discovery

Run discovery without writing a file:

    sudo ./discover_peers.py --iax-config /etc/asterisk/iax_custom.conf --local-office 40423

Write a discovered mapping after reviewing the output:

    sudo ./discover_peers.py \\
      --iax-config /etc/asterisk/iax_custom.conf \\
      --local-office 40423 \\
      --output /opt/meshphone-router/peers.discovered.json \\
      --yes

Discovery matches peer IPs, hostnames, and peer-name fragments against the MeshPhone PBX list. Ambiguous or unmatched peers are reported rather than silently enabled.

## Automated refresh

refresh.py performs the following steps:

1. Discover local IAX peers.
2. Preserve existing manual mappings.
3. Add new discovered mappings.
4. Record unmatched peers and conflicts in the status file.
5. Generate and atomically install meshphone.conf.
6. Reload the Asterisk dialplan.

The FreePBX status module reads:

    /var/lib/meshphone-router/status.json

Install the FreePBX module from freepbx-module/ and schedule refresh.py, for example:

    17 3 * * 0 root /opt/meshphone-router/refresh.py

The current implementation does not perform compile-time health filtering. Runtime Asterisk dialing handles failover across configured first-hop peers.

## Safety

Review generated routes before first activation. Keep a backup of the previous meshphone.conf. If source data is incomplete or route generation fails, retain the last known-good configuration and investigate the status alert.
