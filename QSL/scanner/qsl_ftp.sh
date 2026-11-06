#!/usr/bin/env bash
# Upload combined QSL images using the af4h.net entry in ~/.passwords.
# Usage: qsl_ftp.sh /path/to/card-folder
#        qsl_ftp.sh --all [archive-folder]
set -euo pipefail
FTP_HOST="simba3a.844dm.net"
CREDENTIAL_HOST="af4h.net"
REMOTE_DIR="/home/dmcmorri_af4h/public_html/qslcards/images"
PASSWORD_FILE="$HOME/.passwords"
command -v curl >/dev/null || { echo 'Install curl first.' >&2; exit 1; }
CREDENTIAL=""
while read -r host kind value; do
    if [[ "$host" == "$CREDENTIAL_HOST" && "${kind%:}" == ftp ]]; then
        CREDENTIAL=${value#ftp://}
        CREDENTIAL=${CREDENTIAL%@*}
        break
    fi
done < "$PASSWORD_FILE"
[[ "$CREDENTIAL" == *:* ]] || { echo 'FTP credentials not found.' >&2; exit 1; }
# Pass credentials over stdin, never in process arguments or printed output.
CREDENTIAL=${CREDENTIAL//\\/\\\\}
CREDENTIAL=${CREDENTIAL//\"/\\\"}
transfer() {
    local image=$1 destination=$2
    printf 'FTP: %s\n' "${destination##*/}"
    printf 'user = "%s"\n' "$CREDENTIAL" | curl --config - --silent --show-error --fail \
        --ssl-reqd --connect-timeout 20 --max-time 180 --ftp-create-dirs \
        --upload-file "$image" "ftp://$FTP_HOST/$destination.part" \
        --quote "-RNFR $destination.part" --quote "-RNTO $destination"
}
upload() {
    local image=$1 folder name temporary
    folder=$(dirname -- "$image")
    name="${folder##*/}.jpg"
    if [[ ! -f "$folder/ftp-sent.txt" ]]; then
        if transfer "$image" "$REMOTE_DIR/$name"; then
            date -Is > "$folder/ftp-sent.txt"
        else
            printf 'Combined-image FTP failed: %s\n' "$folder" >&2
            return 1
        fi
    fi
    # Separate fronts keep the QRZ preview free of the back and footer.
    if [[ ! -f "$folder/ftp-front-sent.txt" ]]; then
        local -a fronts im
        shopt -s nullglob
        fronts=("$folder/"*_front.png)
        (( ${#fronts[@]} == 1 )) || { echo "Front image missing: $folder" >&2; return 1; }
        if command -v magick >/dev/null; then im=(magick); else im=(convert); fi
        temporary=$(mktemp --suffix=.jpg)
        if "${im[@]}" "${fronts[0]}" -auto-orient -resize '1200x1200>' -background white -alpha remove -alpha off -colorspace sRGB -quality 90 "$temporary" \
            && transfer "$temporary" "${REMOTE_DIR%/images}/fronts/$name"; then
            date -Is > "$folder/ftp-front-sent.txt"
            rm -- "$temporary"
        else
            rm -- "$temporary"
            printf 'Front-image FTP failed; retry: qsl_ftp.sh %q\n' "$folder" >&2
            return 1
        fi
    fi
}

if [[ "${1:-}" == --all ]]; then
    root=${2:-"$HOME/Pictures/QSL"}
    [[ -d "$root" ]] || { echo 'Archive folder missing.' >&2; exit 1; }
    failed=0
    while IFS= read -r -d '' image; do upload "$image" || failed=1; done < <(find "$root" -type f -name '*_frameo.jpg' -print0)
    exit "$failed"
elif [[ $# == 1 && -d "$1" ]]; then
    shopt -s nullglob
    images=("$1/"*_frameo.jpg)
    (( ${#images[@]} == 1 )) || { echo 'Expected one combined image in card folder.' >&2; exit 1; }
    upload "${images[0]}"
else
    echo 'Usage: qsl_ftp.sh CARD_FOLDER  |  qsl_ftp.sh --all [ARCHIVE_FOLDER]' >&2
    exit 1
fi
