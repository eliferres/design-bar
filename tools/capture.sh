#!/usr/bin/env bash
# Capture a page at the four review widths and hand the shots to a
# fresh-eyes reviewer. The widths are the review panel's contract:
# 320 (small phone), 375 (phone), 768 (tablet), 1280 (desktop).
#
# Usage: bash tools/capture.sh <page.html-or-url> <output-dir>
# Browser: set DESIGN_BAR_BROWSER to a Chrome/Chromium binary, or let
# the script find one. No browser -> plain message, exit 2.
# Extra flags: DESIGN_BAR_FLAGS adds browser flags (some sandboxes need
# --single-process; a normal machine needs nothing).
#
# Trust the PNG, not the browser's exit code: some headless builds exit
# nonzero after writing a perfectly good screenshot, so the only proof
# that matters is a nonzero file on disk. shot_guard.py then reads each
# PNG's bottom rows: content on the last row means the fixed viewport
# cropped the page, and the capture fails loudly instead of shipping a
# silent crop; a clean shot is trimmed to end 48px below its content,
# so tall viewports cost nothing but safety margin.
set -u

WIDTHS="${DESIGN_BAR_WIDTHS:-320 375 768 1280}"
HEIGHT="${DESIGN_BAR_HEIGHT:-2400}"

if [ $# -ne 2 ]; then
  echo "usage: capture.sh <page.html-or-url> <output-dir>"
  exit 2
fi
PAGE="$1"
OUT="$2"

find_browser() {
  if [ -n "${DESIGN_BAR_BROWSER:-}" ]; then
    printf '%s' "$DESIGN_BAR_BROWSER"
    return
  fi
  for candidate in chrome-headless-shell chromium chromium-browser \
    google-chrome google-chrome-stable \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s' "$candidate"
      return
    fi
  done
}

BROWSER="$(find_browser)"
if [ -z "$BROWSER" ]; then
  echo "no Chrome or Chromium found."
  echo "install one, or point DESIGN_BAR_BROWSER at a headless-capable binary."
  exit 2
fi

case "$PAGE" in
  http://*|https://*) TARGET="$PAGE" ;;
  *)
    if [ ! -f "$PAGE" ]; then
      echo "no such file: $PAGE"
      exit 2
    fi
    TARGET="file://$(cd "$(dirname "$PAGE")" && pwd)/$(basename "$PAGE")"
    ;;
esac

mkdir -p "$OUT"
FAILED=0
for width in $WIDTHS; do
  SHOT="$OUT/shot-$width.png"
  # shellcheck disable=SC2086 - DESIGN_BAR_FLAGS is a flag list on purpose
  "$BROWSER" --headless --disable-gpu --hide-scrollbars ${DESIGN_BAR_FLAGS:-} \
    --screenshot="$SHOT" --window-size="$width,$HEIGHT" \
    "$TARGET" >/dev/null 2>&1
  if [ -s "$SHOT" ]; then
    python3 "$(dirname "$0")/shot_guard.py" --trim "$SHOT" >/dev/null 2>&1
    case $? in
      1)
        echo "TRUNCATED $SHOT (content reaches the bottom edge - raise DESIGN_BAR_HEIGHT)"
        FAILED=1
        ;;
      *)
        echo "captured $SHOT"
        ;;
    esac
  else
    echo "FAILED   $SHOT (no file written)"
    FAILED=1
  fi
done

if [ "$FAILED" -ne 0 ]; then
  exit 1
fi
echo
echo "next: hand these shots to a reviewer who did not build the page,"
echo "with panel/REVIEW-BRIEF-TEMPLATE.md. Shots and the ask only -"
echo "never the builder's reasoning."
exit 0
