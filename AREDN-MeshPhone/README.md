# AREDN MeshPhone Route Builder

Builds topology-aware Asterisk MeshPhone dialplan routes from the N2MH MeshPhone administration lists.

The builder:

- Reads the dial-plan and trunk tables from n2mh-web.local.mesh.
- Builds a PBX/trunk graph.
- Finds shortest paths from the local office code to destination office codes.
- Maps configured first-hop office codes to local IAX2 peer names.
- Generates Asterisk routes with runtime failover across enabled peers.

The web data describes topology; local IAX credentials and peer names belong in a site-specific configuration file and must not be committed.

## Configuration

Copy peers.example.json to a private local path and set the local office code and enabled first-hop mappings.

Example:

    {
      "local_office": "40423",
      "peers": {
        "93710": { "peer": "nc8q", "enabled": true }
      }
    }

Run:

    ./routebuilder.py --config /path/to/peers.json --output /etc/asterisk/meshphone.conf

Review and validate the generated file before reloading Asterisk. Use atomic replacement and retain the previous working file when running automatically.
