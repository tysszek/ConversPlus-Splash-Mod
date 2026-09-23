#!/usr/bin/env python3
"""Convert an image to the indexed + RLE frame format used by the analysed Convers+ splash.

A palette JSON is required. The repository includes an observed CS7T theme palette subset.
For best results use a palette captured from the same firmware/theme as the target cluster.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from PIL import Image, ImageOps

FRAME_HEADER = bytes.fromhex("00 00 00 FF 01 00 00 00 00 00 00 00")
WIDTH = 400
HEIGHT = 198


def load_palette(path: Path) -> Dict[int, Tuple[int, int, int]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    colors = obj.get("colors", obj)
    out = {int(k): tuple(int(v) for v in rgb) for k, rgb in colors.items()}
    if not out:
        raise ValueError("Palette contains no colours")
    for idx in out:
        if not 0 <= idx <= 255:
            raise ValueError(f"Palette index outside 0..255: {idx}")
    return out


def resize_cover(img: Image.Image, size=(WIDTH, HEIGHT)) -> Image.Image:
    return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def map_to_palette(img: Image.Image, palette: Dict[int, Tuple[int, int, int]]) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(img.convert("RGB"), dtype=np.int32).reshape(-1, 3)
    indices = np.array(sorted(palette.keys()), dtype=np.uint8)
    colors = np.array([palette[int(i)] for i in indices], dtype=np.int32)

    out_idx = np.empty(arr.shape[0], dtype=np.uint8)
    out_rgb = np.empty((arr.shape[0], 3), dtype=np.uint8)
    chunk = 5000
    for start in range(0, arr.shape[0], chunk):
        part = arr[start:start+chunk]
        diff = part[:, None, :] - colors[None, :, :]
        dist = np.sum(diff * diff, axis=2, dtype=np.int64)
        best = np.argmin(dist, axis=1)
        out_idx[start:start+chunk] = indices[best]
        out_rgb[start:start+chunk] = colors[best].astype(np.uint8)
    return out_idx.reshape(HEIGHT, WIDTH), out_rgb.reshape(HEIGHT, WIDTH, 3)


def rle_encode(indices: bytes) -> bytes:
    src = list(indices)
    out = bytearray()
    i = 0
    n = len(src)
    while i < n:
        value = src[i]
        run = 1
        while i + run < n and src[i + run] == value and run < 0xFE:
            run += 1
        if run >= 2:
            out.extend((run, value))
            i += run
            continue

        start = i
        i += 1
        while i < n and (i - start) < 0xFE:
            value2 = src[i]
            run2 = 1
            while i + run2 < n and src[i + run2] == value2 and run2 < 2:
                run2 += 1
            if run2 >= 2:
                break
            i += 1
        literals = src[start:i]
        out.extend((0, len(literals)))
        out.extend(literals)
    return bytes(out)


def rle_decode(data: bytes, expected: int) -> bytes:
    out = bytearray()
    pos = 0
    while len(out) < expected:
        count = data[pos]
        pos += 1
        if count == 0:
            ln = data[pos]
            pos += 1
            out.extend(data[pos:pos+ln])
            pos += ln
        else:
            value = data[pos]
            pos += 1
            out.extend([value] * count)
    if len(out) != expected:
        raise ValueError("RLE round-trip length mismatch")
    return bytes(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Encode a 400x198 Convers+ splash frame")
    ap.add_argument("image", type=Path)
    ap.add_argument("--palette", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("encoded_splash"))
    ap.add_argument("--fit", choices=["cover", "stretch"], default="cover")
    args = ap.parse_args()

    palette = load_palette(args.palette)
    img = Image.open(args.image).convert("RGB")
    if args.fit == "cover":
        img = resize_cover(img)
    else:
        img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    indices, rgb = map_to_palette(img, palette)
    index_bytes = indices.astype(np.uint8).tobytes()
    rle = rle_encode(index_bytes)
    decoded = rle_decode(rle, WIDTH * HEIGHT)
    if decoded != index_bytes:
        raise SystemExit("RLE verification failed")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "indices.bin").write_bytes(index_bytes)
    (args.out_dir / "splash.rle").write_bytes(rle)
    (args.out_dir / "splash_frame.bin").write_bytes(FRAME_HEADER + rle)
    img.save(args.out_dir / "source_400x198.png")
    Image.fromarray(rgb, "RGB").save(args.out_dir / "preview_exact_palette.png")
    Image.fromarray(rgb, "RGB").resize((WIDTH*4, HEIGHT*4), Image.Resampling.NEAREST).save(
        args.out_dir / "preview_exact_palette_x4.png")

    report = {
        "width": WIDTH,
        "height": HEIGHT,
        "decoded_pixels": WIDTH * HEIGHT,
        "palette_entries_available": len(palette),
        "palette_indices_used": len(np.unique(indices)),
        "rle_bytes": len(rle),
        "frame_bytes": len(rle) + len(FRAME_HEADER),
        "frame_header_hex": FRAME_HEADER.hex(" "),
        "rle_round_trip_ok": True,
    }
    (args.out_dir / "encode_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Encoded 400x198: {len(rle)} B RLE, {len(rle)+12} B complete frame")
    print(f"Palette indices used: {report['palette_indices_used']}")
    print(f"Output: {args.out_dir}")


if __name__ == "__main__":
    main()
