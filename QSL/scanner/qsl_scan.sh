#!/usr/bin/env bash
# Scan one QSL card, save both sides, and build a portrait Frameo image.
# Debian setup: sudo apt install sane-utils imagemagick
# The Brother scanner driver must also be installed.
set -euo pipefail

# ===================== EDIT YOUR SETTINGS HERE =====================
# Leave DEVICE empty to use the first scanner. USB device names can change.
DEVICE=""
SOURCE="Automatic Document Feeder(left aligned,Duplex)"
MODE="24bit Color[Fast]"
DPI=300
AUTO_SIZE=yes
DESKEW=yes

# Used only when AUTO_SIZE=no. These are millimeters; change to fit your card.
SCAN_WIDTH=152.4
SCAN_HEIGHT=110

OUTPUT_DIR="$HOME/Pictures/QSL"
FRAME_WIDTH=1080
FRAME_HEIGHT=1920
BACKGROUND="#17212b"
FONT="DejaVu-Sans"

# ImageMagick rotations are CLOCKWISE. Use 0, 90, 180, or 270.
ROTATE_FRONT=0
ROTATE_BACK=0
SWAP_SIDES=no

# Your tested remote upload settings.
UPLOAD=yes
FRAME_NAME="frame1"
NETWORK="relay"
UPLOAD_TIMEOUT="2m"
FTP_UPLOAD=yes
# ==================================================================

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
usage() {
    printf 'Usage: %s YYYY-MM-DD CALLSIGN\n       %s --retry /path/to/card-folder\n' "$0" "$0"
}
[[ "${1:-}" != --help ]] || { usage; exit 0; }
(( $# == 2 )) || { usage >&2; exit 1; }
mkdir -p -- "$OUTPUT_DIR"
# One job at a time protects the scanner, numbering, and catalog.
exec 9>"$OUTPUT_DIR/.scan.lock"
if ! flock -n 9; then
    printf 'Another QSL job is running. Queued; waiting for it to finish...\n'
    flock 9
fi
CATALOG="$OUTPUT_DIR/catalog.tsv"
if [[ ! -f "$CATALOG" ]]; then
    printf 'timestamp\tqso_date\tcall_sign\tcard_id\tstatus\tfolder\n' > "$CATALOG"
fi
record_status() {
    printf '%s\n' "$1" > "$SESSION/status.txt"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -Is)" "$QSO_DATE" "$CALL" \
        "${SESSION##*/}" "$1" "$SESSION" >> "$CATALOG"
}
send_image() {
    command -v unframeo >/dev/null || { record_status pending; die 'Images saved; unframeo is missing.'; }
    local -a send=(unframeo)
    [[ -z "$FRAME_NAME" ]] || send+=(-frame "$FRAME_NAME")
    send+=(-net "$NETWORK" -timeout "$UPLOAD_TIMEOUT" -fit -caption "$CALL | $QSO_DATE" send "$COMBINED")
    record_status sending
    if "${send[@]}" > "$SESSION/upload.log" 2>&1; then
        record_status sent
        printf 'Sent to Frameo: %s\n' "${SESSION##*/}"
    else
        record_status upload_failed
        cat -- "$SESSION/upload.log" >&2
        printf 'Images saved. Check the frame before retrying to avoid duplicates.\nRetry:\n' >&2
        printf 'bash %q --retry %q\n' "$0" "$SESSION" >&2
        return 1
    fi
}
if [[ "$1" == --retry ]]; then
    SESSION=$(realpath -- "$2")
    [[ -f "$SESSION/metadata.tsv" ]] || die 'Not a new-format card folder (metadata.tsv missing).'
    IFS=$'\t' read -r QSO_DATE CALL STEM < "$SESSION/metadata.tsv"
    COMBINED="$SESSION/${STEM}_frameo.jpg"
    [[ -s "$COMBINED" ]] || die 'Frameo image missing.'
    [[ "$(cat "$SESSION/status.txt")" != sent ]] || die 'Already marked sent; no duplicate upload performed.'
    send_image
    exit
fi
for tool in scanimage date; do
    command -v "$tool" >/dev/null || die "Required program missing: $tool"
done
if command -v magick >/dev/null; then
    IM=(magick)
elif command -v convert >/dev/null; then
    IM=(convert)
else
    die 'Install ImageMagick: sudo apt install imagemagick'
fi

QSO_DATE=$1
CALL=$2
CALL=${CALL^^}
[[ "$CALL" =~ ^[A-Z0-9][A-Z0-9/\ -]{0,39}$ ]] || die 'Invalid call sign (use letters, numbers, /, spaces or hyphens).'
[[ "$QSO_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die 'Use YYYY-MM-DD.'
NORMAL_DATE=$(date -d "$QSO_DATE" +%F 2>/dev/null) || die 'Invalid date.'
[[ "$NORMAL_DATE" == "$QSO_DATE" ]] || die 'Invalid date.'
[[ "$FRAME_WIDTH" =~ ^[0-9]+$ && "$FRAME_HEIGHT" =~ ^[0-9]+$ ]] || die 'Frame dimensions must be integers.'
(( FRAME_WIDTH >= 300 && FRAME_HEIGHT >= 600 )) || die 'Frame dimensions are too small.'

# Replace slashes/spaces in filenames. Keep the original call sign on the image.
SAFE_CALL=${CALL//\//_}
SAFE_CALL=${SAFE_CALL// /_}
STEM="${SAFE_CALL}_${QSO_DATE}"
# Year / call sign / date_call_sequence. Sequence distinguishes repeat cards.
PARENT="$OUTPUT_DIR/${QSO_DATE:0:4}/$SAFE_CALL"
mkdir -p -- "$PARENT"
NUMBER=1
while :; do
    printf -v CARD_ID '%s_%s_%03d' "$QSO_DATE" "$SAFE_CALL" "$NUMBER"
    SESSION="$PARENT/$CARD_ID"
    [[ -e "$SESSION" ]] || break
    NUMBER=$((NUMBER + 1))
done
mkdir -- "$SESSION"
printf '%s\t%s\t%s\n' "$QSO_DATE" "$CALL" "$STEM" > "$SESSION/metadata.tsv"
record_status scanning
mkdir -- "$SESSION/raw" "$SESSION/layout"
trap 'record_status processing_failed; printf "Scan stopped. Files remain in: %s\n" "$SESSION" >&2' ERR

SCAN=(scanimage --format=png "--batch=$SESSION/raw/side-%d.png" --batch-count=2
      --source "$SOURCE" --mode "$MODE" --resolution "$DPI"
      "--AutoDocumentSize=$AUTO_SIZE" "--AutoDeskew=$DESKEW" --SkipBlankPage=no)
[[ -z "$DEVICE" ]] || SCAN+=(--device-name "$DEVICE")
if [[ "$AUTO_SIZE" == no ]]; then
    SCAN+=(-x "$SCAN_WIDTH" -y "$SCAN_HEIGHT")
fi
printf 'Scanning %s — load the card before running this command.\n' "$CARD_ID"
"${SCAN[@]}"
FRONT_RAW="$SESSION/raw/side-1.png"
BACK_RAW="$SESSION/raw/side-2.png"
[[ -s "$FRONT_RAW" && -s "$BACK_RAW" ]] || die "Two sides were not captured. Check $SESSION/raw"
if [[ "$SWAP_SIDES" == yes ]]; then
    FRONT_RAW="$SESSION/raw/side-2.png"
    BACK_RAW="$SESSION/raw/side-1.png"
fi

FRONT="$SESSION/${STEM}_front.png"
BACK="$SESSION/${STEM}_back.png"
COMBINED="$SESSION/${STEM}_frameo.jpg"
"${IM[@]}" "$FRONT_RAW" -auto-orient -background "$BACKGROUND" -rotate "$ROTATE_FRONT" "$FRONT"
"${IM[@]}" "$BACK_RAW" -auto-orient -background "$BACKGROUND" -rotate "$ROTATE_BACK" "$BACK"

# Fit each side into its own panel without cropping or stretching.
MARGIN=$((FRAME_WIDTH / 30))
FOOTER=$((FRAME_HEIGHT / 9))
PANEL_HEIGHT=$(((FRAME_HEIGHT - FOOTER - 3 * MARGIN) / 2))
PANEL_WIDTH=$((FRAME_WIDTH - 2 * MARGIN))
for SIDE in front back; do
    "${IM[@]}" "$SESSION/${STEM}_${SIDE}.png" \
        -resize "${PANEL_WIDTH}x${PANEL_HEIGHT}" \
        -background "$BACKGROUND" -gravity center \
        -extent "${PANEL_WIDTH}x${PANEL_HEIGHT}" "$SESSION/layout/$SIDE.png"
done

# label: automatically fits long call signs inside the available width.
"${IM[@]}" -background "$BACKGROUND" -fill white -font "$FONT" \
    -gravity center -size "${PANEL_WIDTH}x$((FOOTER / 2))" \
    "label:$CALL" "$SESSION/layout/call.png"
"${IM[@]}" -background "$BACKGROUND" -fill white -font "$FONT" \
    -gravity center -size "${PANEL_WIDTH}x$((FOOTER / 3))" \
    "label:$QSO_DATE" "$SESSION/layout/date.png"

"${IM[@]}" -size "${FRAME_WIDTH}x${FRAME_HEIGHT}" "xc:$BACKGROUND" \
    "$SESSION/layout/front.png" -geometry "+${MARGIN}+${MARGIN}" -composite \
    "$SESSION/layout/back.png" -geometry "+${MARGIN}+$((PANEL_HEIGHT + 2 * MARGIN))" -composite \
    "$SESSION/layout/call.png" -geometry "+${MARGIN}+$((FRAME_HEIGHT - FOOTER))" -composite \
    "$SESSION/layout/date.png" -geometry "+${MARGIN}+$((FRAME_HEIGHT - FOOTER / 2))" -composite \
    -colorspace sRGB -sampling-factor 4:4:4 -quality 95 "$COMBINED"
printf '\nSaved front, back, and Frameo image in:\n%s\n' "$SESSION"
record_status ready
# Layout panels are temporary; raw captures and final images are retained.
rm -- "$SESSION/layout/front.png" "$SESSION/layout/back.png" "$SESSION/layout/call.png" "$SESSION/layout/date.png"
rmdir -- "$SESSION/layout"
trap - ERR

if [[ "$FTP_UPLOAD" == yes ]]; then
    FTP_HELPER="$(dirname -- "$(realpath -- "$0")")/qsl_ftp.sh"
    if [[ -f "$FTP_HELPER" ]]; then
        bash "$FTP_HELPER" "$SESSION" || printf 'FTP upload failed; continuing with Frameo. Retry using qsl_ftp.sh.\n' >&2
    else
        printf 'FTP helper missing: install qsl_ftp.sh alongside this script.\n' >&2
    fi
fi

if [[ "$UPLOAD" == yes ]]; then
    send_image
else
    printf 'To send this image after pairing unframeo:\n'
    printf 'bash %q --retry %q\n' "$0" "$SESSION"
fi
