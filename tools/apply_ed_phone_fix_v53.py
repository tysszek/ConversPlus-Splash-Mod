#!/usr/bin/env python3
"""Apply the visible Polish waiting-call wording fix to ED for V5.3.

The ED phone resource uses length-prefixed strings packed back-to-back.  The
requested word is one byte longer than ``Dokladnie``.  We preserve the
resource size and all following offsets by removing only the punctuation from
the adjacent short button label ``Akcept.`` -> ``Akcept``.
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
    "6b8a0a3d72338014570e4493ffb4749299c0f18dcc40a6754f229ec92c7ccab2"
)
PART_NUMBER = "CS7T-14C026-ED"
EXPECTED_ADDR = 0x30000000
EXPECTED_LENGTH = 0x200000
VBF_HEADER_CHECKSUM = re.compile(rb"file_checksum\s*=\s*0x([0-9A-Fa-f]{8})")

# File offset of the length byte immediately before the Polish ``Dokladnie``
# token in the verified 1412-FL ED resource.
DOKLADNIE_LENGTH_RAW_OFFSET = 0xE9FAC


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


def patch_vbf(input_path: Path, output_path: Path) -> dict[str, object]:
    source = input_path.read_bytes()
    input_sha256 = hashlib.sha256(source).hexdigest()
    if input_sha256 != EXPECTED_INPUT_SHA256:
        raise SystemExit(
            "Błąd: wejście nie jest zweryfikowanym ED z bieżącego pakietu PL. "
            f"Oczekiwano {EXPECTED_INPUT_SHA256}, otrzymano {input_sha256}."
        )

    header_end, address, length, source_payload = parse_vbf(source)
    if address != EXPECTED_ADDR or length != EXPECTED_LENGTH:
        raise SystemExit(
            f"Błąd: nieoczekiwany blok ED: adres=0x{address:X}, długość=0x{length:X}."
        )
    payload_start = header_end + 8
    offset = DOKLADNIE_LENGTH_RAW_OFFSET - payload_start
    payload = bytearray(source_payload)

    expected = b"\x09Dokladnie\x07Akcept.\x07"
    if bytes(payload[offset : offset + len(expected)]) != expected:
        raise SystemExit(
            "Błąd: nieoczekiwany układ tekstu ED przy Dokladnie: "
            f"{bytes(payload[offset:offset + len(expected)]).hex()}"
        )

    # Keep the same byte count: 0A + 10-byte "przychodzi" + 06 + 6-byte
    # "Akcept" + the following 0x07 marker.
    replacement = b"\x0Aprzychodzi\x06Akcept\x07"
    if len(replacement) != len(expected):
        raise AssertionError("ED replacement must preserve the resource size.")
    payload[offset : offset + len(replacement)] = replacement

    output = build_vbf(source, bytes(payload))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)

    _, out_address, out_length, out_payload = parse_vbf(output)
    out_header_end = find_header_end(output)
    out_crc16 = struct.unpack_from(">H", output, out_header_end + 8 + out_length)[0]
    block = output[out_header_end : out_header_end + 8 + out_length + 2]
    header_match = VBF_HEADER_CHECKSUM.search(output[:out_header_end])
    stored_crc32 = int(header_match.group(1), 16) if header_match else -1
    if out_crc16 != crc16_ccitt_false(out_payload):
        raise SystemExit("Walidacja ED: CRC16 nie zgadza się.")
    if stored_crc32 != (zlib.crc32(block) & 0xFFFFFFFF):
        raise SystemExit("Walidacja ED: file_checksum nie zgadza się.")

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
        "visible_change": "Dokladnie -> przychodzi",
        "byte_budget_preserved_change": "Akcept. -> Akcept",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(patch_vbf(args.input, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
