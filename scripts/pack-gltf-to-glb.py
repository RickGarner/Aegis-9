#!/usr/bin/env python3
"""Pack a local glTF, binary buffer, and textures into one self-contained GLB."""

from __future__ import annotations

import argparse
import json
import mimetypes
import struct
from pathlib import Path

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def align(data: bytearray, byte: int = 0) -> None:
    data.extend(bytes([byte]) * ((4 - len(data) % 4) % 4))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    root = args.source.parent
    document = json.loads(args.source.read_text(encoding="utf-8"))
    buffers = document.get("buffers", [])
    if len(buffers) != 1 or not buffers[0].get("uri"):
        raise ValueError("Expected exactly one external glTF buffer.")

    binary = bytearray((root / buffers[0]["uri"]).read_bytes())
    align(binary)
    buffers[0].pop("uri", None)

    buffer_views = document.setdefault("bufferViews", [])
    for image in document.get("images", []):
        uri = image.pop("uri", None)
        if not uri:
            continue
        payload = (root / uri).read_bytes()
        offset = len(binary)
        binary.extend(payload)
        view_index = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(payload)})
        image["bufferView"] = view_index
        image["mimeType"] = mimetypes.guess_type(uri)[0] or "application/octet-stream"
        align(binary)

    buffers[0]["byteLength"] = len(binary)
    asset = document.setdefault("asset", {})
    asset["generator"] = f"{asset.get('generator', 'glTF')} + Jarvis local GLB packer"

    json_bytes = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(binary)
    output = bytearray(struct.pack("<4sII", b"glTF", 2, total))
    output.extend(struct.pack("<II", len(json_bytes), JSON_CHUNK))
    output.extend(json_bytes)
    output.extend(struct.pack("<II", len(binary), BIN_CHUNK))
    output.extend(binary)

    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_bytes(output)
    print(f"Wrote {args.destination} ({len(output):,} bytes)")


if __name__ == "__main__":
    main()
