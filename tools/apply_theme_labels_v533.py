#!/usr/bin/env python3
"""Apply the visible Polish colour-theme labels to CD V5.3.2.

The cluster contains two paths for the theme screen: Polish language-table
entries for Dark/Blue and a compact theme descriptor containing Dark/Blue/
Grey/Red.  This patch updates both paths while leaving other language-table
entries untouched.  The existing V5.3.2 string pool has enough free 0xEF
space for the longer Polish labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import apply_menu_labels_v53 as base


EXPECTED_INPUT_SHA256 = (
    "687a85f70138d247db171b01c0262a4cb3a544313d77680e51dbab4bdd20e45a"
)
PART_NUMBER = "CS7T-14C026-CD"

# The common theme descriptor has fixed-size inline fields.  The final field
# ends before the 0xEF free-area marker at 0xD2A82.
INLINE_THEME_FIELDS: list[tuple[str, int, bytes, bytes]] = [
    ("dark_inline", 0xD2A57, b"Dark  \x00\x00\x00\x00\x00", b"Ciemny"),
    ("blue_inline", 0xD2A62, b"Blue\x00\x00\x00\x00\x00\x00\x00", b"Niebieski"),
    ("grey_inline", 0xD2A6D, b"Grey  \x00\x00\x00\x00\x00", b"Szary"),
    ("red_inline", 0xD2A78, b"Red  \x00\x00\x00\x00", b"Czerwony"),
]

# The title pointer inside the common descriptor still points to the English
# literal.  Redirect it to the already verified Polish "Kolory" pool entry.
THEME_DESCRIPTOR_TITLE = (0xD2A49, 0xD2A8E, b"Colour themes")

# Polish is the eighth entry in this 10-language table.  These are the two
# corresponding option pointers observed in the verified V5.2 layout.
POLISH_THEME_POINTERS: list[tuple[str, int, int, bytes]] = [
    ("dark", 0x95F76, 0x85FAE, b"Dark"),
    ("blue", 0x95FC8, 0x85FFA, b"Blue"),
]

POOL_PREFIX = [
    ("forward_alert", b"Ostrz. kolizji\x00"),
    ("driver_alert", b"Czujno\x80\x07\x00"),
    ("colour_themes", b"Kolory\x00"),
    ("advanced", b"Zaawansowane\x00"),
]

POOL_THEME_LABELS = [
    ("dark", b"Ciemny\x00"),
    ("blue", b"Niebieski\x00"),
    ("grey", b"Szary\x00"),
    ("red", b"Czerwony\x00"),
]


def patch_fixed_field(
    payload: bytearray,
    payload_start: int,
    raw_offset: int,
    expected: bytes,
    replacement_text: bytes,
) -> None:
    offset = base.raw_to_payload(raw_offset, payload_start)
    if bytes(payload[offset : offset + len(expected)]) != expected:
        raise ValueError(
            f"Nieoczekiwany motyw pod 0x{raw_offset:X}: "
            f"{bytes(payload[offset:offset + len(expected)])!r}"
        )
    replacement = replacement_text + b"\x00"
    if len(replacement) > len(expected):
        raise ValueError(f"Napis {replacement_text!r} nie mieści się w polu 0x{raw_offset:X}.")
    replacement += b"\x00" * (len(expected) - len(replacement))
    payload[offset : offset + len(expected)] = replacement


def patch_vbf(input_path: Path, output_path: Path) -> dict[str, object]:
    source = input_path.read_bytes()
    input_sha256 = hashlib.sha256(source).hexdigest()
    if input_sha256 != EXPECTED_INPUT_SHA256:
        raise SystemExit(
            "Błąd: wejście nie jest zweryfikowanym CD V5.3.2. "
            f"Oczekiwano {EXPECTED_INPUT_SHA256}, otrzymano {input_sha256}."
        )

    header_end, address, length, source_payload = base.parse_vbf(source)
    if address != base.EXPECTED_ADDR or length != base.EXPECTED_LENGTH:
        raise SystemExit(
            f"Błąd: nieoczekiwany blok CD: adres=0x{address:X}, długość=0x{length:X}."
        )

    payload_start = header_end + 8
    pool_start = base.raw_to_payload(base.NEW_STRING_POOL_RAW_OFFSET, payload_start)
    pool_end = pool_start + base.NEW_STRING_POOL_SIZE
    payload = bytearray(source_payload)

    # Confirm the existing V5.3.2 pool before appending anything.
    cursor = pool_start
    existing_vas: dict[str, int] = {}
    for name, encoded in POOL_PREFIX:
        if bytes(payload[cursor : cursor + len(encoded)]) != encoded:
            raise ValueError(f"Nieoczekiwany istniejący napis puli: {name!r}.")
        existing_vas[name] = base.EXPECTED_ADDR + cursor
        cursor += len(encoded)

    new_vas: dict[str, int] = {"colour_themes": existing_vas["colour_themes"]}
    for name, encoded in POOL_THEME_LABELS:
        if cursor + len(encoded) > pool_end:
            raise SystemExit("Błąd: zabrakło miejsca w puli napisów motywów.")
        if bytes(payload[cursor : cursor + len(encoded)]) != b"\xEF" * len(encoded):
            raise ValueError(f"Obszar puli dla {name!r} nie jest wolny.")
        payload[cursor : cursor + len(encoded)] = encoded
        new_vas[name] = base.EXPECTED_ADDR + cursor
        cursor += len(encoded)

    # Redirect the common descriptor title and the two Polish language-table
    # options to the new pool entries.
    base.patch_pointer(
        payload,
        payload_start,
        THEME_DESCRIPTOR_TITLE[0],
        THEME_DESCRIPTOR_TITLE[1],
        new_vas["colour_themes"],
        THEME_DESCRIPTOR_TITLE[2],
    )
    for name, target_raw, reference_raw, old_text in POLISH_THEME_POINTERS:
        base.patch_pointer(
            payload,
            payload_start,
            target_raw,
            reference_raw,
            new_vas[name],
            old_text,
        )

    # Translate the four labels stored directly in the active theme
    # descriptor.  Field sizes are preserved exactly.
    for _, raw_offset, expected, replacement_text in INLINE_THEME_FIELDS:
        patch_fixed_field(payload, payload_start, raw_offset, expected, replacement_text)

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
        raise SystemExit("Walidacja V5.3.3: CRC16 nie zgadza się.")
    if stored_crc32 != (base.zlib.crc32(block) & 0xFFFFFFFF):
        raise SystemExit("Walidacja V5.3.3: file_checksum nie zgadza się.")

    return {
        "input_sha256": input_sha256,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "part_number": PART_NUMBER,
        "version": "V5.3.3",
        "theme_descriptor_title": "Colour themes -> Kolory",
        "inline_theme_labels": {
            "Dark": "Ciemny",
            "Blue": "Niebieski",
            "Grey": "Szary",
            "Red": "Czerwony",
        },
        "polish_theme_table_refs_patched": len(POLISH_THEME_POINTERS),
        "address": f"0x{out_address:X}",
        "length": f"0x{out_length:X}",
        "crc16": f"0x{out_crc16:04X}",
        "file_checksum": f"0x{stored_crc32:08X}",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(patch_vbf(args.input, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
