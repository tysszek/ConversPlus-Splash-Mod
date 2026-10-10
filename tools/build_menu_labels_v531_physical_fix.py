#!/usr/bin/env python3
"""Build the V5.3.2 menu-label correction confirmed on the physical cluster.

V5.3 redirected the Polish menu-table entries, but the cluster also uses a
small set of direct title pointers for the visible menu rows and submenu
headers.  V5.3.1 keeps the original V5.3 patch and redirects those direct
title pointers to the same verified Polish string pool.
"""

from __future__ import annotations

import argparse
import hashlib
import tempfile
from pathlib import Path

import apply_menu_labels_v53 as base


# Direct title pointers observed in the verified V5.2 CD image.  The same
# strings are visible in the physical-cluster photos supplied after V5.3.
DIRECT_TITLE_REFS: dict[str, list[tuple[int, int, bytes]]] = {
    "forward_alert": [
        (0x849EF, 0x84BB2, b"Forward Alert"),
        (0x85701, 0x8573A, b"Forward Alert"),
        (0x865FD, 0x86642, b"Forward Alert"),
    ],
    "driver_alert": [
        (0x849CF, 0x84C42, b"Driver Alert"),
        (0x87262, 0x87376, b"Driver Alert"),
    ],
    "colour_themes": [
        (0x84EE9, 0x84FA2, b"Colour themes"),
        (0x85EED, 0x85F16, b"Colour themes"),
    ],
    "advanced": [
        (0x84A33, 0x84DF2, b"Advanced"),
        (0x85DE5, 0x85E06, b"Advanced"),
    ],
}


def _new_pool_vas(payload: bytes, payload_start: int) -> dict[str, int]:
    values = {
        "forward_alert": b"Ostrz. kolizji\x00",
        # The ASCII ``o`` is required: Czujn + o + ś + ć.
        "driver_alert": b"Czujno\x80\x07\x00",
        "colour_themes": b"Kolory\x00",
        "advanced": b"Zaawansowane\x00",
    }
    vas: dict[str, int] = {}
    pool_start = base.raw_to_payload(base.NEW_STRING_POOL_RAW_OFFSET, payload_start)
    pool_end = pool_start + base.NEW_STRING_POOL_SIZE
    for name, value in values.items():
        offset = payload.find(value, pool_start, pool_end)
        if offset < 0:
            raise ValueError(f"Nie znaleziono nowego napisu {name!r} w puli V5.3.")
        vas[name] = base.EXPECTED_ADDR + offset
    return vas


def patch_vbf(input_path: Path, output_path: Path) -> dict[str, object]:
    with tempfile.NamedTemporaryFile(
        prefix="convers_v53_base_", suffix=".vbf", dir=output_path.parent, delete=False
    ) as handle:
        intermediate = Path(handle.name)

    try:
        base.patch_vbf(input_path, intermediate)
        source = intermediate.read_bytes()
        header_end, address, length, source_payload = base.parse_vbf(source)
        if address != base.EXPECTED_ADDR or length != base.EXPECTED_LENGTH:
            raise SystemExit("Błąd: nieoczekiwany blok CD po zbudowaniu V5.3.")

        payload_start = header_end + 8
        payload = bytearray(source_payload)
        new_vas = _new_pool_vas(source_payload, payload_start)

        changed_refs = 0
        for name, entries in DIRECT_TITLE_REFS.items():
            for target_raw, reference_raw, old_text in entries:
                base.patch_pointer(
                    payload,
                    payload_start,
                    target_raw,
                    reference_raw,
                    new_vas[name],
                    old_text,
                )
                changed_refs += 1

        output = base.build_vbf(source, bytes(payload))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(output)

        _, out_address, out_length, out_payload = base.parse_vbf(output)
        out_header_end = base.find_header_end(output)
        out_crc16 = int.from_bytes(
            output[out_header_end + 8 + out_length : out_header_end + 10 + out_length],
            "big",
        )
        block = output[out_header_end : out_header_end + 8 + out_length + 2]
        header_match = base.VBF_HEADER_CHECKSUM.search(output[:out_header_end])
        stored_crc32 = int(header_match.group(1), 16) if header_match else -1
        if out_crc16 != base.crc16_ccitt_false(out_payload):
            raise SystemExit("Walidacja V5.3.1: CRC16 nie zgadza się.")
        if stored_crc32 != base.zlib.crc32(block) & 0xFFFFFFFF:
            raise SystemExit("Walidacja V5.3.1: file_checksum nie zgadza się.")

        return {
            "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256(output).hexdigest(),
            "part_number": base.PART_NUMBER,
            "version": "V5.3.2",
            "direct_title_references_patched": changed_refs,
            "address": f"0x{out_address:X}",
            "length": f"0x{out_length:X}",
            "crc16": f"0x{out_crc16:04X}",
            "file_checksum": f"0x{stored_crc32:08X}",
            "visible_polish_labels": {
                "Forward Alert": "Ostrz. kolizji",
                "Driver Alert": "Czujność",
                "Colour themes": "Kolory",
                "Advanced": "Zaawansowane",
            },
        }
    finally:
        intermediate.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    import json

    print(json.dumps(patch_vbf(args.input, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
