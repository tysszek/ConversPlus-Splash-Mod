#!/usr/bin/env python3
"""Relocate a prepared splash frame into free ED space and patch its descriptor.

The default offsets are specific to the analysed CS7T-14C026-ED firmware.
The tool writes a NEW VBF, verifies both VBF checksums, and re-decodes the inserted frame.
"""
from __future__ import annotations

import argparse
import binascii
import json
import re
import zlib
from pathlib import Path

DEFAULT_PAYLOAD_OFFSET = 0x426
DEFAULT_BINARY_OFFSET = 0x41E
DEFAULT_DESCRIPTOR_OFFSET = 0x08EFBC
DEFAULT_FRAME_LOCATION = 0x120000
WIDTH = 400
HEIGHT = 198
STRIDE = 400


def parse_int(value: str) -> int:
    return int(value, 0)


def rle_decode(data: bytes, expected: int) -> bytes:
    out = bytearray()
    pos = 0
    while len(out) < expected:
        if pos >= len(data):
            raise ValueError("RLE ended early")
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
        raise ValueError(f"Decoded {len(out)} bytes, expected {expected}")
    return bytes(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Patch CS7T-14C026-ED.vbf with a relocated Convers+ splash")
    ap.add_argument("input_ed", type=Path)
    ap.add_argument("frame", type=Path, help="12-byte frame header + RLE data, from encode_splash.py")
    ap.add_argument("output_ed", type=Path, help="must be a new output path")
    ap.add_argument("--payload-offset", type=parse_int, default=DEFAULT_PAYLOAD_OFFSET)
    ap.add_argument("--binary-offset", type=parse_int, default=DEFAULT_BINARY_OFFSET)
    ap.add_argument("--descriptor-offset", type=parse_int, default=DEFAULT_DESCRIPTOR_OFFSET)
    ap.add_argument("--frame-location", type=parse_int, default=DEFAULT_FRAME_LOCATION,
                    help="new frame address relative to ED payload")
    ap.add_argument("--allow-other-part", action="store_true",
                    help="allow patching when sw_part_number is not CS7T-14C026-ED")
    ap.add_argument("--force-nonempty", action="store_true",
                    help="allow writing over bytes other than 0xEF (NOT recommended)")
    args = ap.parse_args()

    if args.input_ed.resolve() == args.output_ed.resolve():
        raise SystemExit("Refusing in-place modification. Choose a different output file.")

    raw = bytearray(args.input_ed.read_bytes())
    frame = args.frame.read_bytes()
    if len(frame) < 13:
        raise SystemExit("Frame is unexpectedly short")
    expected_header = bytes.fromhex("00 00 00 FF 01 00 00 00 00 00 00 00")
    if frame[:12] != expected_header:
        raise SystemExit("Unexpected frame header")

    part_match = re.search(rb'sw_part_number\s*=\s*"([^"]+)"', raw[:0x1000])
    part = part_match.group(1).decode("ascii", "replace") if part_match else "UNKNOWN"
    if part != "CS7T-14C026-ED" and not args.allow_other_part:
        raise SystemExit(f"Unexpected sw_part_number={part}. Use --allow-other-part only after manual verification.")

    d = args.payload_offset + args.descriptor_offset
    width = int.from_bytes(raw[d:d+2], "big")
    height = int.from_bytes(raw[d+2:d+4], "big")
    stride = int.from_bytes(raw[d+4:d+6], "big")
    if (width, height, stride) != (WIDTH, HEIGHT, STRIDE):
        raise SystemExit(f"Descriptor geometry is {width}x{height}, stride={stride}; expected 400x198/400")

    target = args.payload_offset + args.frame_location
    end = target + len(frame)
    if end > len(raw) - 2:
        raise SystemExit("New frame does not fit inside VBF payload")
    old_target = raw[target:end]
    free_ok = all(b == 0xEF for b in old_target)
    if not free_ok and not args.force_nonempty:
        raise SystemExit("Target region is not entirely 0xEF. Refusing to overwrite it.")

    expected_indices = rle_decode(frame[12:], WIDTH * HEIGHT)

    raw[target:end] = frame
    data_location = args.frame_location + 12
    data_ptr = 0x30000000 | data_location
    frame_ptr = 0x30000000 | args.frame_location
    raw[d+8:d+12] = data_ptr.to_bytes(4, "big")
    raw[d+12:d+16] = frame_ptr.to_bytes(4, "big")

    crc16 = binascii.crc_hqx(bytes(raw[args.payload_offset:-2]), 0xFFFF)
    raw[-2:] = crc16.to_bytes(2, "big")

    checksum_match = re.search(rb'file_checksum\s*=\s*0x([0-9A-Fa-f]{8});', raw[:0x1000])
    if not checksum_match:
        raise SystemExit("Could not find file_checksum field")
    crc32 = zlib.crc32(bytes(raw[args.binary_offset:])) & 0xFFFFFFFF
    raw[checksum_match.start(1):checksum_match.end(1)] = f"{crc32:08X}".encode("ascii")

    args.output_ed.parent.mkdir(parents=True, exist_ok=True)
    args.output_ed.write_bytes(raw)

    check = args.output_ed.read_bytes()
    m2 = re.search(rb'file_checksum\s*=\s*0x([0-9A-Fa-f]{8});', check[:0x1000])
    file_checksum_ok = bool(m2) and int(m2.group(1), 16) == (zlib.crc32(check[args.binary_offset:]) & 0xFFFFFFFF)
    crc16_ok = int.from_bytes(check[-2:], "big") == binascii.crc_hqx(check[args.payload_offset:-2], 0xFFFF)
    pointer_data_ok = check[d+8:d+12] == data_ptr.to_bytes(4, "big")
    pointer_frame_ok = check[d+12:d+16] == frame_ptr.to_bytes(4, "big")
    saved_frame = check[target:target+len(frame)]
    frame_bytes_ok = saved_frame == frame
    decoded_saved = rle_decode(saved_frame[12:], WIDTH * HEIGHT)
    rle_ok = decoded_saved == expected_indices

    audit = {
        "input": str(args.input_ed),
        "output": str(args.output_ed),
        "sw_part_number": part,
        "descriptor_offset": hex(args.descriptor_offset),
        "frame_location": hex(args.frame_location),
        "data_location": hex(data_location),
        "frame_pointer": hex(frame_ptr),
        "data_pointer": hex(data_ptr),
        "frame_bytes": len(frame),
        "target_was_all_EF": free_ok,
        "file_checksum_crc32": f"0x{crc32:08X}",
        "payload_crc16": f"0x{crc16:04X}",
        "checks": {
            "file_checksum_ok": file_checksum_ok,
            "payload_crc16_ok": crc16_ok,
            "data_pointer_ok": pointer_data_ok,
            "frame_pointer_ok": pointer_frame_ok,
            "frame_bytes_ok": frame_bytes_ok,
            "rle_round_trip_ok": rle_ok,
        },
    }
    audit_path = args.output_ed.with_suffix(args.output_ed.suffix + ".audit.json")
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    if not all(audit["checks"].values()):
        raise SystemExit(f"PATCH WRITTEN BUT AUDIT FAILED — see {audit_path}")

    print("Patch and audit OK")
    print(f"Output: {args.output_ed}")
    print(f"Audit:  {audit_path}")
    print(f"Frame @ 0x{args.frame_location:06X}, data @ 0x{data_location:06X}")
    print(f"file_checksum=0x{crc32:08X}; payload CRC16=0x{crc16:04X}")


if __name__ == "__main__":
    main()
