# Duplex QSL scanner

Bash workflow for a Brother DS-740D on Linux: capture both sides, save archival PNGs, create a portrait JPEG, and upload to Frameo and an FTP gallery.

```bash
sudo apt install sane-utils imagemagick curl
# Install the Brother Linux scanner driver separately, then verify scanimage -L.
mkdir -p ~/.local/bin
install -m 755 qsl_scan.sh qsl_ftp.sh ~/.local/bin/
qsl_scan.sh 2020-04-30 am95ward
```

Load one card before running the command. Date is the QSO date. Edit the settings at the top of each script for your scanner, frame, and hosting account. Ensure ~/.local/bin is on PATH.

The script saves `~/Pictures/QSL/YYYY/CALL/YYYY-MM-DD_CALL_001/`, including separate front/back PNGs, combined 1080 × 1920 JPEG, raw captures, metadata, and upload status. Repeat cards receive sequential numbers. `catalog.tsv` records processing history. Concurrent jobs wait for a lock; keep their terminals open and load the correct card before its turn. Ordering of waiting jobs is not guaranteed.

## Frameo

Install the unofficial [unframeo client](https://github.com/borje/unframeo), pair using a current friend code, and check `unframeo -net relay info`. This setup uses `frame1`, relay mode, fit mode, and a two-minute timeout.

```bash
qsl_scan.sh --retry '/full/path/to/card-folder'
```

Check the frame before retrying after ambiguous failures. A successful uploader exit marks the card sent; it does not verify display. Already-sent cards are not resent by the retry command.

## FTP gallery

`qsl_ftp.sh` reads the af4h.net FTP entry from `~/.passwords`, in the local format `af4h.net ftp: ftp://USERNAME:PASSWORD@af4h.net`. Never commit that file or actual credentials. Restrict it to mode 600. Customize the host, credential key, and remote folder before using elsewhere. TLS certificate verification remains enabled; this hosting account uses `simba3a.844dm.net`.

```bash
qsl_ftp.sh --all
qsl_ftp.sh '/full/path/to/card-folder'
```

The helper publishes only combined JPEGs, uploads through a temporary filename, and records `ftp-sent.txt` after success. Remove that marker to republish an edited image. FTP failure does not prevent Frameo delivery. The gallery implementation is in [`af4h.net/qslcards`](../../af4h.net/qslcards); card images and credentials are runtime data, not repository content.

For physical filing, use year, call sign, and QSO date; write the card ID on an archival sleeve. Back up the entire archive.

## QRZ front-only preview

FTP also publishes a front-only JPEG under `qslcards/fronts/`, with its own
`ftp-front-sent.txt` success marker. Run `qsl_ftp.sh --all` to backfill existing
cards. The image URL `https://af4h.net/qslcards/random-front.php` serves one
random front per request. Link it to the full slideshow in a QRZ biography:

```html
<a href="https://af4h.net/qslcards/" target="_blank" rel="noopener">
  <img src="https://af4h.net/qslcards/random-front.php"
       alt="A random card from AF4H's QSL collection"
       width="600" style="max-width:100%;height:auto;border:0;">
</a>
```

This is a still image per page load, not a timed slideshow. The endpoint sends
no-cache headers, but QRZ or an image proxy may cache its response.
