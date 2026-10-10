#!/usr/bin/env python3
"""Translate the two additional active colour-theme labels in CD V5.3.3.

The six theme records in the verified V5.3.3 menu point to two final labels
that were still stored as ``Green`` and ``Lunar Sky``.  This patch changes
only those two strings in place; the record pointers, RAM flags and the four
earlier Polish labels remain unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import apply_menu_labels_v53 as base


EXPECTED_INPUT_SHA256 = (
    "212ef4f577a5acdce4ab276b9daff3f057647dc7b5317f437d09586ef4584756"
)
PART_NUMBER = "CS7T-14C026-CD"
EXPECTED_ADDR = 0x5000
EXPECTED_LENGTH = 0xFB000

THEME_ROWS = [
    ("green", 0xD7804, 0x40008A61, 0xD78A0, b"Green\x00", b"Zielony\x00"),
    (
        "lunar_sky",
        0xD784C,
        0x40008A1D,
        0xD78B0,
        b"Lunar Sky\x00",
        b"Nocne niebo\x00",
    ),
]


def read_u32(payload: bytes, payload_start: int, va: int) -> int:
    del payload_start
    offset = va - EXPECTED_ADDR
    return int.from_bytes(payload[offset : offset + 4], "big")


def patch_label(
    payload: bytearray,
    payload_start: int,
    raw_offset: int,
    old_text: bytes,
    new_text: bytes,
) -> None:
    del payload_start
    offset = raw_offset - EXPECTED_ADDR
    if bytes(payload[offset : offset + len(old_text)]) != old_text:
        raise ValueError(
            f"Nieoczekiwany napis pod 0x{raw_offset:X}: "
            f"{bytes(payload[offset:offset + len(old_text)])!r}"
        )
    payload[offset : offset + len(new_text)] = new_text


def verify_theme_row(
    payload: bytes,
    payload_start: int,
    record_va: int,
    flag_va: int,
    label_va: int,
    label: bytes,
) -> None:
    if read_u32(payload, payload_start, record_va) != 0x37:
        raise ValueError(f"Nieoczekiwany rekord motywu pod 0x{record_va:X}.")
    pointer = read_u32(payload, payload_start, record_va + 4)
    if pointer != label_va:
        raise ValueError(
            f"Motyw pod 0x{record_va:X} wskazuje 0x{pointer:X}, "
            f"oczekiwano 0x{label_va:X}."
        )
    for field in range(record_va + 8, record_va + 0x30, 4):
        if read_u32(payload, payload_start, field) != label_va:
            raise ValueError(f"Nieoczekiwany wskaźnik motywu pod 0x{field:X}.")
    if read_u32(payload, payload_start, record_va + 0x3C) != 0:
        raise ValueError(f"Nieoczekiwany offset flagi pod 0x{record_va + 0x3C:X}.")
    if read_u32(payload, payload_start, record_va + 0x40) != flag_va:
        raise ValueError(f"Nieoczekiwana flaga motywu pod 0x{record_va + 0x40:X}.")
    label_offset = label_va - EXPECTED_ADDR
    if bytes(payload[label_offset : label_offset + len(label)]) != label:
        raise ValueError(f"Nieoczekiwany tekst motywu pod 0x{label_va:X}.")


def patch_vbf(input_path: Path, output_path: Path) -> dict[str, object]:
    source = input_path.read_bytes()
    input_sha256 = hashlib.sha256(source).hexdigest()
    if input_sha256 != EXPECTED_INPUT_SHA256:
        raise SystemExit(
            "Błąd: wejście nie jest zweryfikowanym CD V5.3.3. "
            f"Oczekiwano {EXPECTED_INPUT_SHA256}, otrzymano {input_sha256}."
        )

    header_end, address, length, source_payload = base.parse_vbf(source)
    if address != EXPECTED_ADDR or length != EXPECTED_LENGTH:
        raise SystemExit(
            f"Błąd: nieoczekiwany blok CD: adres=0x{address:X}, długość=0x{length:X}."
        )
    payload_start = header_end + 8
    payload = bytearray(source_payload)

    for name, record_va, flag_va, label_va, old_text, new_text in THEME_ROWS:
        verify_theme_row(source_payload, payload_start, record_va, flag_va, label_va, old_text)
        patch_label(payload, payload_start, label_va, old_text, new_text)

    output = base.build_vbf(source, bytes(payload))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)

    _, out_address, out_length, out_payload = base.parse_vbf(output)
    out_header_end = base.find_header_end(output)
    out_crc16 = struct.unpack_from(">H", output, out_header_end + 8 + out_length)[0]
    block = output[out_header_end : out_header_end + 8 + out_length + 2]
    header_match = base.VBF_HEADER_CHECKSUM.search(output[:out_header_end])
    stored_crc32 = int(header_match.group(1), 16) if header_match else -1
    if out_crc16 != base.crc16_ccitt_false(out_payload):
        raise SystemExit("Walidacja V5.3.4: CRC16 nie zgadza się.")
    if stored_crc32 != (base.zlib.crc32(block) & 0xFFFFFFFF):
        raise SystemExit("Walidacja V5.3.4: file_checksum nie zgadza się.")

    # Verify the complete records again after writing the new labels.
    for name, record_va, flag_va, label_va, _old_text, new_text in THEME_ROWS:
        verify_theme_row(out_payload, payload_start, record_va, flag_va, label_va, new_text)

    return {
        "input_sha256": input_sha256,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "part_number": PART_NUMBER,
        "version": "V5.3.4",
        "theme_labels": {"Green": "Zielony", "Lunar Sky": "Nocne niebo"},
        "active_theme_rows_preserved": True,
        "address": f"0x{out_address:X}",
        "length": f"0x{out_length:X}",
        "crc16": f"0x{out_crc16:04X}",
        "file_checksum": f"0x{stored_crc32:08X}",
        "changed_payload_bytes": sum(a != b for a, b in zip(source_payload, out_payload)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(patch_vbf(args.input, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
