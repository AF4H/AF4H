# af4h.net

Source for https://af4h.net/ and https://af4h.net/gapacket/.

## Layout

- `index.html`: AF4H homepage.
- `gapacket/`: PHP/SQLite community station map.
- `gapacket/config.example.php`: blank example only; never deploy credentials into the web root.

## Hosting

Deploy to the existing PHP hosting account and its domain web root.
Upload `index.html` to the web root, and the four application files (`index.html`, `style.css`, `app.js`, `api.php`) to its `gapacket/` folder.
Changes under `af4h.net/` on `main` automatically deploy through `.github/workflows/deploy-af4h.yml`. The workflow can also be run manually from the Actions tab on `main`. Failed deployments appear as failed Actions runs.\n\nThe receiver at `/deploy.php` verifies GitHub OIDC signatures, issuer, audience, immutable repository/owner IDs, workflow path, main branch, event, token expiration, and the current main commit. No stored deployment password or SSH key is needed. Pull requests and other branches cannot deploy. The receiver downloads that exact commit and publishes only after the workflow checks PHP and JavaScript syntax.\n\nOnly website file types are deployed. Dot directories, deployment tooling, Markdown, credential configuration, and databases are excluded. The receiver itself is installed separately from `.deploy/endpoint.php`; changes to that file require deliberate installation on the host. Previously deployed files removed from source are removed from the website. Other pre-existing server files are preserved. Private QRZ configuration and station data stay outside the deployment destination.\n\nThe latest five deployment staging folders and backups are retained privately in the map storage directory, alongside `deployment.json` (the live commit and file manifest). File replacements are atomic individually; a multi-file release is not a single atomic directory switch. Do not add secrets to website source. Protect `main` according to who should be allowed to publish.

Requires PHP 8+, PDO SQLite, cURL, SimpleXML, APCu, and HTTPS.

## Private runtime files

Directory: a `private/gapacket` folder beside `public_html` (mode 700).

- `config.php`: QRZ username/password (mode 600). Use the blank example as a guide; keep the subscribed account credentials exclusively on the server.
- `stations.sqlite`: shared station database. Back this up privately; never commit it.

The API resolves this private directory relative to its deployment path. Preserve the `public_html/gapacket` layout or adjust the private path in `api.php` when hosting elsewhere.

## Map behavior

QRZ fills an editable address and coordinates when available. Changed addresses require the operator to place a pin manually; no address geocoding service is configured. Public station data includes callsign, coordinates, status, and update time. Street addresses and edit-key hashes are excluded from public responses.

Additions need no edit key. Updating an existing station requires confirming the popup; anyone can confirm an update, and callsign ownership is self-reported. Additional IDs such as AF4H/14 are separate stations, with QRZ lookup using AF4H for a trailing numeric suffix. Stored street addresses are excluded from public responses, and lookup refills the address from QRZ. Deletion remains protected by the original edit key and is no longer offered in the interface. Existing database records are preserved. Email verification is a deferred idea and is not implemented.

The map uses Leaflet and OpenStreetMap tiles with attribution. Statuses are Online (green), Ready (blue), and Interested (amber).

## Verification

PHP/JavaScript syntax, live page responses, station create/update/delete, wrong-key rejection, CSRF rejection, and exclusion of private fields were checked during initial deployment. Authenticated AF4H QRZ lookup returned an address and coordinates successfully. Temporary test entries were removed.
