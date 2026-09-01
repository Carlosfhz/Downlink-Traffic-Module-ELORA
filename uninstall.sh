#!/usr/bin/env bash
#
# uninstall.sh — restore the upstream ELoRa helper files saved by install.sh.
#
#   usage: ./uninstall.sh /path/to/ns-3-dev
#
set -euo pipefail

REL="contrib/elora/helper"

NS3="${1:?usage: $0 /path/to/ns-3-dev}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP="$HERE/.backup"

NS3="$(cd "$NS3" 2>/dev/null && pwd)" || { echo "no such directory: $1" >&2; exit 1; }
DST="$NS3/$REL"

[[ -d "$BACKUP" ]] || { echo "nothing to restore: no $BACKUP" >&2; exit 1; }
[[ -d "$DST" ]]    || { echo "missing $REL in $NS3" >&2; exit 1; }

restored=0
shopt -s nullglob
for path in "$BACKUP"/*; do
    f="$(basename "$path")"
    cp "$path" "$DST/$f"
    touch "$DST/$f"
    echo "restored $f"
    restored=$((restored + 1))
done
shopt -u nullglob

echo
echo "restored $restored file(s) — rebuild with:  cd $NS3 && ./ns3 build"
