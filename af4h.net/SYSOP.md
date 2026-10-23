# Sysop portal and telemetry

Portal: `/gapacket/sysop.php`. Public station history: `/gapacket/history.php?callsign=CALLSIGN`.

## Access

A registered sysop requests a login link by base callsign. The link goes only to the sysop registry email on file, never an address supplied in the login request. The initial authorized account is AF4H. Additional sysops and their emails are managed by existing sysops. Map registration or an API key does not make someone a sysop.

Login links expire in 15 minutes, work once, and require the user to select Sign in. The raw token travels in a URL fragment, is removed from the address bar, and is never sent to the server until the sign-in button is used. Sessions expire after eight hours. Registry removal or email changes invalidate existing sessions and links. The last sysop cannot be removed. Every sysop has the same management permissions; there is no separate owner role in this version.

All sysop mutations require a signed-in session and CSRF token. Sysop station changes take effect immediately, invalidate pending end-user approvals for the station, and are audited. End-user additions/changes/removals still require the existing QRZ-email approval flow.

## Audit and public history

The append-only SQLite audit table records time, actor type and ID, entity ID, action, and before/after snapshots. Station records existing at migration receive an explicitly labeled baseline. Earlier changes cannot be reconstructed. The sysop portal shows paginated audit events, including private before/after station addresses. Public station history returns only action, actor, time, and previous/new station status; it omits addresses, emails, API key hashes, and login secrets. Raw API keys and login tokens are never recorded in audit data. SQLite triggers reject audit updates/deletes through ordinary queries; this is not an external tamper-proof logging service.

## Telemetry API keys

Create a named key in the portal with an explicit comma-separated list of currently listed station IDs, scopes (`links`, `metrics`, or both), and expiry from 1–365 days. The raw key is displayed once and stored hashed. Revoke a key in the portal to stop subsequent requests. API keys confer no sysop privileges.

Send HTTPS `POST /gapacket/telemetry.php`, with `Content-Type: application/json` and `Authorization: Bearer YOUR_KEY`. Do not put keys in URLs.

```json
{
  "links": [{
    "id": "reporter-node1-node2-145070000",
    "a_node": "K1ABC",
    "z_node": "W1ABC/14",
    "frequency_hz": 145070000,
    "capacity_bps": 9600,
    "status": "online",
    "last_seen": "2026-10-23T20:00:00Z"
  }],
  "metrics": [{
    "station_id": "K1ABC",
    "observed_at": "2026-10-23T20:00:00Z",
    "throughput_bps": 1200,
    "error_count": 2,
    "retry_count": 3,
    "packet_count": 100
  }]
}
```

The payload is an illustrative format example, not real connectivity or measurements. Use current timestamps.

- Each link must include at least one listed station in the key's exact station scope. Other endpoints may be unlisted; they never create markers or plotted lines.
- IDs distinguish multiple channels. A key owns link IDs it first creates and cannot overwrite links owned by other keys or unowned sysop/test links. A sysop can edit any link; editing preserves its reporter ownership. Revoking an owner key prevents further reporting with it. To transfer ownership, a sysop currently removes the link and lets the new reporter create it again.
- Link capacity is 300–57,600 integer bps; frequency is positive integer Hz or null. Status is online, offline, or disabled. Stale link timestamps are rejected; timestamps more than five minutes in the future are rejected.
- Metrics must reference a currently listed station in the key scope, and timestamps must be within 30 days and no more than five minutes in the future. Unknown measurements should be omitted or null, not zero.
- Error, retry, and packet counts are increments for the reporting interval, **not cumulative lifetime counters**. Report disjoint intervals for a station to avoid double counting between keys. Samples with the same key, station, and timestamp are idempotent (duplicates are ignored).
- Public history shows sample-average throughput and summed interval counters for 24 hours and 7 days. Retry rate is `sum(retries) / sum(packets) × 100` when both are reported. This is station-level telemetry in this version, not per-channel measurements. No measurements means “Not reported.”
- Limits: 64 KiB request, up to 100 links and 100 metric samples per request, 60 requests/minute per key. Raw metrics older than 30 days are pruned during telemetry ingestion. Station audit records are retained.

Map revision checks include station changes, links, and incoming metric samples. An open station history panel updates when the map sees a changed revision, within roughly five seconds while the page is visible.

## Private storage and operations

Registry, hashed login tokens, key hashes/scopes, telemetry samples, and audit snapshots live in the existing private station SQLite database outside the web root. Back it up privately. Keep QRZ and SMTP configuration in the existing private config file. No secrets are needed in GitHub.

The deployment includes an initial private database backup and baseline audit migration. The portal cannot restore backups or modify/delete audit records. Telemetry writers are deliberately unable to add, edit, or remove station registrations.
