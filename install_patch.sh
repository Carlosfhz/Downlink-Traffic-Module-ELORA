#!/usr/bin/env bash
#
# install.sh — overlay custom ELoRa helper files onto an ns-3 tree.
#
#   usage: ./install.sh /path/to/ns-3-dev [--dry-run]
#
# Every file in PATCH_FILES/ is copied into contrib/elora/helper/.
# The first time a file is replaced, the upstream original is saved
# into .backup/ so uninstall.sh can restore it.
#
set -euo pipefail
 
REL="contrib/elora/helper"
 
# ---------------------------------------------------------------- args
DRY_RUN=0
NS3=""
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
        *)         NS3="$arg" ;;
    esac
done
 
if [[ -z "$NS3" ]]; then
    echo "usage: $0 /path/to/ns-3-dev [--dry-run]" >&2
    exit 1
fi
 
# ---------------------------------------------------------------- paths
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/PATCH_FILES"
BACKUP="$HERE/.backup"
 
NS3="$(cd "$NS3" 2>/dev/null && pwd)" || { echo "no such directory: $1" >&2; exit 1; }
DST="$NS3/$REL"
 
# ---------------------------------------------------------------- checks
[[ -d "$SRC" ]]     || { echo "error: missing $SRC" >&2; exit 1; }
[[ -x "$NS3/ns3" ]] || { echo "error: not an ns-3 tree (no ./ns3): $NS3" >&2; exit 1; }
[[ -d "$DST" ]]     || { echo "error: missing $REL — is ELoRa installed?" >&2; exit 1; }
 
shopt -s nullglob
FILES=("$SRC"/*.cc "$SRC"/*.h)
shopt -u nullglob
[[ ${#FILES[@]} -gt 0 ]] || { echo "error: no .cc/.h files in $SRC" >&2; exit 1; }
 
echo "source:      $SRC"
echo "destination: $DST"
[[ $DRY_RUN -eq 1 ]] && echo "mode:        DRY RUN (nothing will be written)"
echo
 
# Warn if the original lorawan module is also present: ELoRa is derived
# from it, shares these filenames, and the two conflict when built together.
for other in "$NS3/src/lorawan" "$NS3/contrib/lorawan"; do
    if [[ -d "$other" ]]; then
        echo "WARNING: found ${other#$NS3/} alongside elora."
        echo "         These modules conflict. Make sure your build actually"
        echo "         compiles elora:  ./ns3 clean && ./ns3 configure \\"
        echo "                              --enable-modules \"elora;tap-bridge;csma\""
        echo
    fi
done
 
# ---------------------------------------------------------------- install
installed=0; identical=0; missing=0
 
for path in "${FILES[@]}"; do
    f="$(basename "$path")"
    target="$DST/$f"
 
    if [[ ! -f "$target" ]]; then
        echo "WARNING  $f — no such file upstream (renamed, moved, or new)"
        missing=$((missing + 1))
    elif cmp -s "$path" "$target"; then
        echo "skip     $f — already identical to the installed version"
        identical=$((identical + 1))
        continue
    else
        # Save the pristine upstream copy, but only the very first time,
        # so a second run never overwrites the backup with our own file.
        if [[ ! -f "$BACKUP/$f" && $DRY_RUN -eq 0 ]]; then
            mkdir -p "$BACKUP"
            cp -p "$target" "$BACKUP/$f"
            echo "backup   $f -> .backup/$f"
        fi
    fi
 
    if [[ $DRY_RUN -eq 0 ]]; then
        cp "$path" "$target"    # plain cp: fresh mtime so ninja rebuilds
        touch "$target"
    fi
    echo "install  $f"
    installed=$((installed + 1))
done
 
# ---------------------------------------------------------------- summary
echo
echo "installed: $installed   unchanged: $identical   not-found-upstream: $missing"
 
if [[ $installed -eq 0 && $identical -gt 0 ]]; then
    echo
    echo "Nothing was changed: every file in PATCH_FILES/ is byte-identical to"
    echo "the one already in $REL. Either the overlay is already installed, or"
    echo "PATCH_FILES/ still holds unmodified upstream copies."
fi
 
if [[ $installed -gt 0 && $DRY_RUN -eq 0 ]]; then
    echo
    echo "now rebuild:  cd $NS3 && ./ns3 build"
fi

 
