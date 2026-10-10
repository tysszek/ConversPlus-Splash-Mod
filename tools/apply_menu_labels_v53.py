#!/usr/bin/env python3
"""Build the visible Polish menu-label patch V5.3 on top of CD V5.2.

Only the Polish records that are displayed by the cluster are redirected to
new strings stored in an already unused 0xEF area.  Other language copies and
unused/system records are deliberately left untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path


EXPECTED_INPUT_SHA256 = (
    "21058ce5f64949e7926e2225eda00c06b43e5308ecd77a651f5ca0f96a631d49"
)
PART_NUMBER = "CS7T-14C026-CD"
EXPECTED_ADDR = 0x5000
EXPECTED_LENGTH = 0xFB000
VBF_HEADER_CHECKSUM = re.compile(rb"file_checksum\s*=\s*0x([0-9A-Fa-f]{8})")

# These are file offsets in the fixed, verified V5.2 VBF.  The script converts
# them to payload offsets after checking the VBF header.
PAYLOAD_STRING_REFS: dict[str, list[tuple[int, int]]] = {
    # Polish language slot 7 in the Ford language order.
    "forward_alert": [
        (0x92D77, 0x8575A),
        (0x952E2, 0x84BCE),
        (0x957CF, 0x8665E),
    ],
    "driver_alert": [
        (0x93944, 0x87396),
        (0x95754, 0x84C62),
    ],
    "colour_themes": [(0x95F1C, 0x85F36), (0x95F1C, 0xD2AAE)],
    "advanced": [(0x94306, 0x85E22), (0x955D3, 0x84E12)],
}

CRUISE_CONTROL_POLISH_OFFSETS = [0xBE3EB, 0xBF3BD, 0xBF955, 0xBF98F]

# Existing V5.2 M0RTAR data ends before this area.  The whole range is 0xEF in
# the source image and is used as a string pool for the redirected labels.
NEW_STRING_POOL_RAW_OFFSET = 0xD943D
NEW_STRING_POOL_SIZE = 0x80


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def find_header_end(data: bytes) -> int:
    depth = 0
    for index, value in enumerate(data[:16384]):
        if value == ord("{"):
            depth += 1
        elif value == ord("}"):
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("Nie znaleziono końca nagłówka VBF.")


def parse_vbf(data: bytes) -> tuple[int, int, int, bytes]:
    header_end = find_header_end(data)
    address, length = struct.unpack_from(">II", data, header_end)
    payload_start = header_end + 8
    payload_end = payload_start + length
    if payload_end + 2 != len(data):
        raise ValueError("Nieprawidłowy rozmiar bloku VBF.")
    return header_end, address, length, data[payload_start:payload_end]


def build_vbf(template: bytes, payload: bytes) -> bytes:
    header_end = find_header_end(template)
    address, length = struct.unpack_from(">II", template, header_end)
    if len(payload) != length:
        raise ValueError("Rozmiar payloadu nie pasuje do szablonu VBF.")
    block = struct.pack(">II", address, length) + payload
    block += struct.pack(">H", crc16_ccitt_false(payload))
    checksum = zlib.crc32(block) & 0xFFFFFFFF
    header = template[:header_end].decode("ascii")
    header, count = re.subn(
        r"(file_checksum\s*=\s*)0x[0-9A-Fa-f]{8}",
        lambda match: f"{match.group(1)}0x{checksum:08X}",
        header,
    )
    if count != 1:
        raise ValueError("Nie znaleziono pojedynczego file_checksum w VBF.")
    return header.encode("ascii") + block


def raw_to_payload(raw_offset: int, payload_start: int) -> int:
    result = raw_offset - payload_start
    if result < 0:
        raise ValueError(f"Offset 0x{raw_offset:X} jest przed payloadem VBF.")
    return result


def patch_pointer(
    payload: bytearray,
    payload_start: int,
    target_raw: int,
    reference_raw: int,
    new_va: int,
    old_text: bytes,
) -> None:
    target = raw_to_payload(target_raw, payload_start)
    reference = raw_to_payload(reference_raw, payload_start)
    if payload[target : target + len(old_text)] != old_text:
        raise ValueError(
            f"Nieoczekiwany tekst pod 0x{target_raw:X}: "
            f"{bytes(payload[target:target + len(old_text)])!r}"
        )
    old_va = EXPECTED_ADDR + target
    old_pointer = old_va.to_bytes(3, "big")
    if payload[reference : reference + 3] != old_pointer:
        raise ValueError(
            f"Nieoczekiwany wskaźnik pod 0x{reference_raw:X}: "
            f"{bytes(payload[reference:reference + 3]).hex()} "
            f"!= {old_pointer.hex()}"
        )
    if not 0 <= new_va <= 0xFFFFFF:
        raise ValueError("Nowy adres tekstu nie mieści się w wskaźniku 24-bit.")
    payload[reference : reference + 3] = new_va.to_bytes(3, "big")


def patch_vbf(input_path: Path, output_path: Path) -> dict[str, object]:
    source = input_path.read_bytes()
    input_sha256 = hashlib.sha256(source).hexdigest()
    if input_sha256 != EXPECTED_INPUT_SHA256:
        raise SystemExit(
            "Błąd: wejście nie jest aktualnym CD V5.2 Menu Labels V1. "
            f"Oczekiwano {EXPECTED_INPUT_SHA256}, otrzymano {input_sha256}."
        )

    header_end, address, length, source_payload = parse_vbf(source)
    if address != EXPECTED_ADDR or length != EXPECTED_LENGTH:
        raise SystemExit(
            f"Błąd: nieoczekiwany blok CD: adres=0x{address:X}, długość=0x{length:X}."
        )
    payload_start = header_end + 8
    pool = raw_to_payload(NEW_STRING_POOL_RAW_OFFSET, payload_start)
    if bytes(source_payload[pool : pool + NEW_STRING_POOL_SIZE]) != b"\xEF" * NEW_STRING_POOL_SIZE:
        raise SystemExit("Błąd: obszar puli napisów nie jest wolnym obszarem 0xEF.")

    payload = bytearray(source_payload)
    new_strings = {
        "forward_alert": b"Ostrz. kolizji",
        # Ford single-byte glyphs: 0x80 = ś, 0x07 = ć.
        # The ASCII ``o`` is required: Czujn + o + ś + ć.
        "driver_alert": b"Czujno\x80\x07",
        "colour_themes": b"Kolory",
        "advanced": b"Zaawansowane",
    }
    new_vas: dict[str, int] = {}
    cursor = pool
    for name, text in new_strings.items():
        encoded = text + b"\x00"
        if cursor + len(encoded) > pool + NEW_STRING_POOL_SIZE:
            raise SystemExit("Błąd: zabrakło miejsca w puli nowych napisów.")
        payload[cursor : cursor + len(encoded)] = encoded
        new_vas[name] = EXPECTED_ADDR + cursor
        cursor += len(encoded)

    old_texts = {
        "forward_alert": b"Forward Alert",
        "driver_alert": b"Driver Alert",
        "colour_themes": b"Tematy kolor.",
        "advanced": b"Advanced",
    }
    for name, entries in PAYLOAD_STRING_REFS.items():
        for target_raw, reference_raw in entries:
            patch_pointer(
                payload,
                payload_start,
                target_raw,
                reference_raw,
                new_vas[name],
                old_texts[name],
            )

    cruise_replacement = b"Tempomat" + b" " * (len(b"Cruise Control") - len(b"Tempomat"))
    if len(cruise_replacement) != len(b"Cruise Control"):
        raise AssertionError("Cruise Control replacement must preserve the field size.")
    for raw_offset in CRUISE_CONTROL_POLISH_OFFSETS:
        offset = raw_to_payload(raw_offset, payload_start)
        if bytes(payload[offset : offset + len(b"Cruise Control")]) != b"Cruise Control":
            raise ValueError(f"Nieoczekiwany Cruise Control pod 0x{raw_offset:X}.")
        payload[offset : offset + len(cruise_replacement)] = cruise_replacement

    output = build_vbf(source, bytes(payload))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)

    _, out_address, out_length, out_payload = parse_vbf(output)
    out_crc16 = struct.unpack_from(">H", output, find_header_end(output) + 8 + out_length)[0]
    block_start = find_header_end(output)
    block = output[block_start : block_start + 8 + out_length + 2]
    header_match = VBF_HEADER_CHECKSUM.search(output[:block_start])
    stored_crc32 = int(header_match.group(1), 16) if header_match else -1
    if out_crc16 != crc16_ccitt_false(out_payload):
        raise SystemExit("Walidacja CD: CRC16 nie zgadza się.")
    if stored_crc32 != (zlib.crc32(block) & 0xFFFFFFFF):
        raise SystemExit("Walidacja CD: file_checksum nie zgadza się.")

    changed = sum(a != b for a, b in zip(source_payload, out_payload))
    return {
        "input_sha256": input_sha256,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "part_number": PART_NUMBER,
        "address": f"0x{out_address:X}",
        "length": f"0x{out_length:X}",
        "changed_payload_bytes": changed,
        "crc16": f"0x{out_crc16:04X}",
        "file_checksum": f"0x{stored_crc32:08X}",
        "visible_polish_labels": {
            "Forward Alert": "Ostrz. kolizji",
            "Driver Alert": "Czujność",
            "Colour themes": "Kolory",
            "Cruise Control": "Tempomat",
            "Advanced": "Zaawansowane",
        },
        "cruise_control_fields": len(CRUISE_CONTROL_POLISH_OFFSETS),
        "other_language_copies_left_untouched": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(patch_vbf(args.input, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
