#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
  echo "USAGE: ${0} CALLSIGN [DATE:YYYY-MM-DD]"
  echo "   or: ${0} QSL CALLSIGN [DATE:YYYY-MM-DD]"
  exit 255
fi

if [ $# -ge 2 ] && [[ "${1^^}" == "QSL" || "${1^^}" == "SWL" || "${1^^}" == "HFTIX" ]]; then
  shift
fi

exec python3 "${SCRIPT_DIR}/qslindex.py" scan "$@"
