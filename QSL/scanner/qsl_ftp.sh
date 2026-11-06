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
upload() {
    local image=$1 folder name
    folder=$(dirname -- "$image")
    name="${folder##*/}.jpg"
    [[ ! -f "$folder/ftp-sent.txt" ]] || return 0
    printf 'FTP: %s\n' "$name"
    if printf 'user = "%s"\n' "$CREDENTIAL" | curl --config - --silent --show-error --fail \
        --ssl-reqd --connect-timeout 20 --max-time 180 --ftp-create-dirs \
        --upload-file "$image" "ftp://$FTP_HOST/$REMOTE_DIR/$name.part" \
        --quote "-RNFR $REMOTE_DIR/$name.part" --quote "-RNTO $REMOTE_DIR/$name"; then
        date -Is > "$folder/ftp-sent.txt"
    else
        printf 'FTP failed; retry with: qsl_ftp.sh %q\n' "$folder" >&2
        return 1
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
