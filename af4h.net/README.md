# af4h.net

Source for https://af4h.net/ and https://af4h.net/gapacket/.

## Layout

- `index.html`: AF4H homepage.
- `gapacket/`: PHP/SQLite community station map.
- `gapacket/config.example.php`: blank example only; never deploy credentials into the web root.

## Hosting

Deploy to the existing PHP hosting account and its domain web root.
Upload `index.html` to the web root, and the four application files (`index.html`, `style.css`, `app.js`, `api.php`) to its `gapacket/` folder.
GitHub stores source; pushing here does not automatically deploy the website.

Requires PHP 8+, PDO SQLite, cURL, SimpleXML, APCu, and HTTPS.

## Private runtime files

Directory: a `private/gapacket` folder beside `public_html` (mode 700).

- `config.php`: QRZ username/password (mode 600). Use the blank example as a guide; keep the subscribed account credentials exclusively on the server.
- `stations.sqlite`: shared station database. Back this up privately; never commit it.

The API resolves this private directory relative to its deployment path. Preserve the `public_html/gapacket` layout or adjust the private path in `api.php` when hosting elsewhere.

## Map behavior

QRZ fills an editable address and coordinates when available. Changed addresses require the operator to place a pin manually; no address geocoding service is configured. Public station data includes callsign, coordinates, status, and update time. Street addresses and edit-key hashes are excluded from public responses.

First registration returns a private edit key, stored in the operator's browser and displayed for safekeeping. The key is required to update or remove a station. Callsigns are self-reported: QRZ lookup does not verify operator ownership. Shared workstations should be used with care because the browser retains edit keys.

The map uses Leaflet and OpenStreetMap tiles with attribution. Statuses are Online (green), Ready (blue), and Interested (amber).

## Verification

PHP/JavaScript syntax, live page responses, station create/update/delete, wrong-key rejection, CSRF rejection, and exclusion of private fields were checked during initial deployment. Authenticated AF4H QRZ lookup returned an address and coordinates successfully. Temporary test entries were removed.
