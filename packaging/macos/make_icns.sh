#!/usr/bin/env bash
# Generate packaging/PyReconstruct.icns from the app logo (macOS only; uses the
# system `sips` + `iconutil`). Run from the repo root before PyInstaller.
set -euo pipefail

SRC="PyReconstruct/assets/img/logo.png"

WORK="$(mktemp -d)"
ICONSET="$WORK/PyReconstruct.iconset"
mkdir -p "$ICONSET"

for s in 16 32 64 128 256 512; do
    d=$((s * 2))
    sips -z "$s" "$s" "$SRC" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
    sips -z "$d" "$d" "$SRC" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done

mkdir -p packaging
iconutil -c icns "$ICONSET" -o packaging/PyReconstruct.icns
rm -rf "$WORK"
echo "wrote packaging/PyReconstruct.icns"
