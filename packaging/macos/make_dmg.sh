#!/usr/bin/env bash
# Build dist/PyReconstruct.app into a .dmg with a drag-to-Applications alias.
# Uses hdiutil (built into macOS) on a staging folder that holds the app plus an
# /Applications symlink -- no AppleScript, so it works on headless CI runners
# (create-dmg's window-styling step times out there).
#   PYR_PUBLIC=<version> ARCH=arm64 bash packaging/macos/make_dmg.sh
set -euo pipefail

: "${PYR_PUBLIC:?set PYR_PUBLIC to the public version string}"
ARCH="${ARCH:-x86_64}"
APP="dist/PyReconstruct.app"
OUT="PyReconstruct-${PYR_PUBLIC}-macOS-${ARCH}.dmg"

[ -d "$APP" ] || { echo "error: $APP not found (build with PyInstaller first)" >&2; exit 1; }
rm -f "$OUT"

STAGE="$(mktemp -d)/PyReconstruct"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"   # drag-and-drop target in the mounted dmg
cp "$(dirname "$0")/dmg-readme.txt" "$STAGE/Read Before First Launch.txt"  # unsigned-app first-launch help

# hdiutil create intermittently fails with "Resource busy" on CI runners when a
# stale diskimages-helper still holds a disk image. Retry with cleanup + backoff.
make_dmg() {
    hdiutil create -volname "PyReconstruct ${PYR_PUBLIC}" -srcfolder "$STAGE" \
        -fs HFS+ -format UDZO -ov "$OUT"
}
for attempt in 1 2 3 4 5; do
    if make_dmg; then break; fi
    [ "$attempt" -eq 5 ] && { echo "error: hdiutil create failed after 5 attempts" >&2; exit 1; }
    echo "hdiutil create failed (attempt $attempt; likely 'Resource busy') -- cleaning up and retrying" >&2
    rm -f "$OUT"
    killall diskimages-helper 2>/dev/null || true   # release a stale helper holding the image
    sleep $((attempt * 5))
done

[ -f "$OUT" ] || { echo "error: hdiutil did not produce $OUT" >&2; exit 1; }
echo "wrote $OUT (with drag-to-Applications alias)"
