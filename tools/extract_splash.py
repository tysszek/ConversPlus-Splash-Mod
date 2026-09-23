#!/usr/bin/env python3
"""Extract and decode the Ford Convers+ startup splash from CS7T-14C026-ED.vbf.

Known-good defaults are for the analysed facelift Convers+ firmware:
  descriptor: 0x08EFBC (relative to ED payload)
  VBF payload file offset: 0x426

The script does not modify firmware.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image


def parse_int(value: str) -> int:
    return int(value, 0)


def load_palette(path: Path | None) -> Dict[int, Tuple[int, int, int]]:
    if path is None:
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    colors = obj.get("colors", obj)
    out: Dict[int, Tuple[int, int, int]] = {}
    for key, rgb in colors.items():
        out[int(key)] = tuple(int(v) for v in rgb)
    return out


def rle_decode(data: bytes, expected_len: int) -> bytes:
    out = bytearray()
    pos = 0
    while len(out) < expected_len:
        if pos >= len(data):
            raise ValueError("RLE ended before expected number of pixels was decoded")
        count = data[pos]
        pos += 1
        if count == 0:
            if pos >= len(data):
                raise ValueError("Truncated literal RLE packet")
            literal_len = data[pos]
            pos += 1
            if literal_len == 0:
                raise ValueError("Zero-length literal packet is not supported")
            if pos + literal_len > len(data):
                raise ValueError("Literal packet extends past input")
            out.extend(data[pos:pos + literal_len])
            pos += literal_len
        else:
            if pos >= len(data):
                raise ValueError("Truncated run RLE packet")
            value = data[pos]
            pos += 1
            out.extend([value] * count)
    if len(out) != expected_len:
        raise ValueError(f"Decoded {len(out)} pixels, expected {expected_len}")
    return bytes(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract a Convers+ 400x198 indexed/RLE splash from ED VBF")
    ap.add_argument("ed_vbf", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("extracted_splash"))
    ap.add_argument("--payload-offset", type=parse_int, default=0x426,
                    help="file offset where ED payload begins (default: 0x426)")
    ap.add_argument("--descriptor-offset", type=parse_int, default=0x08EFBC,
                    help="descriptor offset relative to payload (default: 0x08EFBC)")
    ap.add_argument("--palette", type=Path,
                    help="optional JSON mapping index -> [R,G,B] for a colour preview")
    args = ap.parse_args()

    raw = args.ed_vbf.read_bytes()
    p = args.payload_offset + args.descriptor_offset
    if p + 20 > len(raw):
        raise SystemExit("Descriptor falls outside file")

    width = int.from_bytes(raw[p:p+2], "big")
    height = int.from_bytes(raw[p+2:p+4], "big")
    stride = int.from_bytes(raw[p+4:p+6], "big")
    reserved = int.from_bytes(raw[p+6:p+8], "big")
    data_ptr = int.from_bytes(raw[p+8:p+12], "big")
    frame_ptr = int.from_bytes(raw[p+12:p+16], "big")
    draw_fn = int.from_bytes(raw[p+16:p+20], "big")

    data_off = data_ptr & 0x00FFFFFF
    frame_off = frame_ptr & 0x00FFFFFF
    frame_file = args.payload_offset + frame_off
    data_file = args.payload_offset + data_off

    if data_file >= len(raw) or frame_file >= len(raw):
        raise SystemExit("Descriptor pointers point outside VBF")
    if data_off - frame_off != 12:
        print(f"WARNING: data-frame delta is {data_off-frame_off}, expected 12")

    frame_header = raw[frame_file:data_file]
    expected = width * height
    indices = rle_decode(raw[data_file:], expected)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "indices.bin").write_bytes(indices)
    (args.out_dir / "frame_header.bin").write_bytes(frame_header)

    gray = Image.frombytes("L", (width, height), indices)
    gray.save(args.out_dir / "indices_grayscale.png")

    palette = load_palette(args.palette)
    missing = set(indices) - set(palette)
    if palette:
        rgb = bytearray()
        for idx in indices:
            rgb.extend(palette.get(idx, (255, 0, 255)))
        Image.frombytes("RGB", (width, height), bytes(rgb)).save(args.out_dir / "preview_palette.png")

    report = {
        "width": width,
        "height": height,
        "stride": stride,
        "reserved": reserved,
        "descriptor_offset": hex(args.descriptor_offset),
        "frame_pointer": hex(frame_ptr),
        "data_pointer": hex(data_ptr),
        "frame_offset": hex(frame_off),
        "data_offset": hex(data_off),
        "drawing_function": hex(draw_fn),
        "frame_header_hex": frame_header.hex(" "),
        "decoded_pixels": len(indices),
        "unique_indices": len(set(indices)),
        "palette_missing_indices": sorted(missing) if palette else None,
    }
    (args.out_dir / "extract_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Extracted: {width}x{height}, stride={stride}")
    print(f"Frame: 0x{frame_off:06X}, data: 0x{data_off:06X}")
    print(f"Decoded pixels: {len(indices)}; unique indices: {len(set(indices))}")
    if palette and missing:
        print(f"WARNING: palette JSON lacks {len(missing)} used indices; they are shown magenta")
    print(f"Output: {args.out_dir}")


if __name__ == "__main__":
    main()
