# Network connectivity layer

The public read API (`gapacket/api.php?action=list`) returns approved stations, link records, a revision hash, and server time. Browsers check every five seconds while visible and on focus. Unchanged revisions preserve popups and avoid rebuilding the map; time-based state transitions also change the revision. Approved additions, edits, removals, and link updates therefore appear on open maps within about five seconds, subject to network latency.

## Future push API (not implemented)

No public ingestion endpoint or credentials have been created. The future authenticated push endpoint can upsert records into the private SQLite database's `node_links` table. It must not add stations or bypass the existing email approval flow. Payload validation, authorization, request limits, stale update rejection, and idempotency belong in that endpoint.

Proposed record:
```json
{"id":"stable-link-id","a_node":"K1ABC","z_node":"W1ABC/14","frequency_hz":145070000,"capacity_bps":9600,"status":"online","last_seen":"2026-10-23T18:00:00Z","source":"telemetry"}
```
The frequency above is an illustrative format example, not the frequency of a real link.

- `id`: stable, unique per connection/channel; multiple channels between the same nodes need distinct IDs.
- Node IDs: canonical uppercase exact station IDs, including numeric slash suffix when applicable. No automatic matching from a suffixed ID to its base station.
- `frequency_hz`: integer hertz, or null if unknown.
- `capacity_bps`: integer bit rate; display widths span 300–57,600 bps logarithmically from 2–10 pixels. Out-of-range display widths are clamped. Capacity is not measured throughput; baud and bps are only equivalent for appropriate modulation.
- `status`: online, offline, or disabled.
- `last_seen`: ISO 8601 UTC timestamp of the latest successful observation.
- `source`: telemetry or test; test records are clearly labeled.
- `updated`: ISO 8601 UTC ingestion timestamp (database field).

## Display rules

Online and last seen within one hour: green. Explicit offline, or stale over one hour: dark grey, dashed. Last seen over three days: light grey, dashed. Explicit disabled or last seen over seven days: no line. Records remain available in hover/click details even when hidden.

A line requires both exact endpoint IDs to exist in the approved station list. Link records never create map markers. Hovering a listed station or tapping it displays every reported incident link, its other endpoint, frequency, capacity, reported status, effective state, and last-seen time. Unplotted links explain the missing endpoint or disabled state.

## Requested live test

A source=test record connects AF4H and N2IRZ at 9,600 bps. Its frequency is null because none was supplied. It uses real approved station locations, is labeled TEST LINK, and ages normally unless replaced by telemetry. It is test data, not a claim of measured connectivity.
