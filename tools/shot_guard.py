#!/usr/bin/env python3
"""Refuse a truncated screenshot; trim the blank canvas off a good one.

capture.sh shoots a fixed-height viewport, so a page taller than the
viewport is cropped and a shorter one leaves a tail of dead canvas.
This guard decodes the PNG's bottom scanlines and does two jobs:

  shot_guard.py <shot.png>          check only: fail loudly when the
                                    bottom row carries content (the
                                    shot is likely truncated)
  shot_guard.py --trim <shot.png>   the same check, then rewrite the
                                    file so it ends 48px below the
                                    last content row

The trim never touches pixels: PNG scanlines only depend on the row
above, so cutting the filtered stream after the keep-line and patching
the header height is an exact bottom crop.

A uniform bottom row is not proof nothing was cut - a crop can land in
the whitespace between sections. It is the honest cheap check; the
README's limitations section says exactly that.

Exit codes: 0 = shot ends clean (trimmed if asked), 1 = content on the
bottom row (raise DESIGN_BAR_HEIGHT and recapture), 2 = usage error or
a PNG this guard cannot read (capture.sh treats 2 as "guard skipped").
"""

import struct
import sys
import zlib
from typing import List, Tuple

SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def read_png(
    path: str,
) -> Tuple[int, int, int, bytes, List[Tuple[bytes, bytes]]]:
    """Return (width, height, channels, scanline stream, chunk list)."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        print(f"error: cannot read {path}: {exc}")
        sys.exit(2)
    if data[:8] != SIGNATURE:
        print(f"error: not a PNG: {path}")
        sys.exit(2)
    pos = 8
    width = height = channels = None
    idat = []
    chunks = []
    while pos + 8 <= len(data):
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        pos += 8
        chunk = data[pos:pos + length]
        pos += length + 4
        chunks.append((ctype, chunk))
        if ctype == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if depth != 8 or interlace != 0 or color not in CHANNELS:
                print(f"error: unsupported PNG layout in {path}")
                sys.exit(2)
            channels = CHANNELS[color]
        elif ctype == b"IDAT":
            idat.append(chunk)
        elif ctype == b"IEND":
            break
    if width is None or not idat:
        print(f"error: malformed PNG: {path}")
        sys.exit(2)
    return width, height, channels, zlib.decompress(b"".join(idat)), chunks


def unfilter_row(row: bytes, prev: bytearray, channels: int) -> bytearray:
    """Reconstruct one scanline from its filter byte and raw bytes."""
    kind, line = row[0], bytearray(row[1:])
    stride = len(line)
    if kind == 0:
        return line
    if kind == 1:
        for i in range(channels, stride):
            line[i] = (line[i] + line[i - channels]) & 0xFF
        return line
    if kind == 2:
        for i in range(stride):
            line[i] = (line[i] + prev[i]) & 0xFF
        return line
    if kind == 3:
        for i in range(stride):
            left = line[i - channels] if i >= channels else 0
            line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        return line
    for i in range(stride):
        left = line[i - channels] if i >= channels else 0
        up = prev[i]
        corner = prev[i - channels] if i >= channels else 0
        estimate = left + up - corner
        distances = (
            abs(estimate - left), abs(estimate - up), abs(estimate - corner)
        )
        if distances[0] <= distances[1] and distances[0] <= distances[2]:
            predictor = left
        elif distances[1] <= distances[2]:
            predictor = up
        else:
            predictor = corner
        line[i] = (line[i] + predictor) & 0xFF
    return line


def bottom_row(width: int, height: int, channels: int, raw: bytes) -> bytearray:
    """Decode and return the last scanline.

    Fast path: walk up from the bottom past 'up'-filtered all-zero rows
    (each identical to the row above) until a row that decodes alone;
    fall back to a full top-down unfilter when the walk hits a filter
    that needs real neighbor data.
    """
    stride = width * channels
    row_len = 1 + stride
    target = height - 1
    while target >= 0:
        row = raw[target * row_len:(target + 1) * row_len]
        if row[0] == 2 and not any(row[1:]):
            target -= 1
            continue
        if row[0] in (0, 1):
            return unfilter_row(row, bytearray(stride), channels)
        break
    prev = bytearray(stride)
    for y in range(max(target, 0) + 1):
        row = raw[y * row_len:(y + 1) * row_len]
        prev = unfilter_row(row, prev, channels)
    return prev


PAD_ROWS = 48


def last_content_row(
    width: int, height: int, channels: int, raw: bytes, anchor: bytes
) -> int:
    """Walk up from the bottom past rows that render as the anchor color.

    Only rows the walk can decode standalone are consumed ('up'-filtered
    all-zero rows repeat the row above; 'none'/'sub' rows decode alone);
    any other filter stops the walk conservatively, keeping more rows.
    """
    stride = width * channels
    row_len = 1 + stride
    blank = bytes(anchor) * width
    y = height - 1
    while y > 0:
        row = raw[y * row_len:(y + 1) * row_len]
        if row[0] == 2 and not any(row[1:]):
            y -= 1
            continue
        if row[0] in (0, 1):
            if bytes(unfilter_row(row, bytearray(stride), channels)) == blank:
                y -= 1
                continue
        break
    return y


def trim(
    path: str,
    width: int,
    height: int,
    channels: int,
    raw: bytes,
    chunks: List[Tuple[bytes, bytes]],
    anchor: bytes,
) -> None:
    """Rewrite the PNG so it ends PAD_ROWS below the last content row."""
    keep = min(last_content_row(width, height, channels, raw, anchor)
               + 1 + PAD_ROWS, height)
    if keep >= height:
        print(f"shot already tight: {path}")
        return
    row_len = 1 + width * channels
    out = [SIGNATURE]
    for ctype, body in chunks:
        if ctype == b"IHDR":
            body = struct.pack(">I", width) + struct.pack(">I", keep) + body[8:]
        elif ctype == b"IDAT":
            continue
        if ctype == b"IEND":
            idat = zlib.compress(raw[:keep * row_len], 9)
            payload = b"IDAT" + idat
            out.append(struct.pack(">I", len(idat)) + payload
                       + struct.pack(">I", zlib.crc32(payload)))
        payload = ctype + body
        out.append(struct.pack(">I", len(body)) + payload
                   + struct.pack(">I", zlib.crc32(payload)))
    with open(path, "wb") as fh:
        fh.write(b"".join(out))
    print(f"trimmed {path}: {height} -> {keep} rows")


def main(argv: List[str]) -> int:
    args = [a for a in argv[1:] if a != "--trim"]
    do_trim = "--trim" in argv[1:]
    if len(args) != 1:
        print("usage: shot_guard.py [--trim] <shot.png>")
        return 2
    path = args[0]
    width, height, channels, raw, chunks = read_png(path)
    row = bottom_row(width, height, channels, raw)
    first_pixel = bytes(row[:channels])
    if bytes(row) != first_pixel * width:
        print(f"content on the bottom row: {path}")
        print("the shot is likely truncated - raise DESIGN_BAR_HEIGHT and recapture.")
        return 1
    if do_trim:
        trim(path, width, height, channels, raw, chunks, first_pixel)
    else:
        print(f"bottom row uniform: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
