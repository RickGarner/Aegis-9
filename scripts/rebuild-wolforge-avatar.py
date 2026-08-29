#!/usr/bin/env python3
"""Build the proportion-corrected Wolforge v2 GLB without changing its animation contract."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

JSON_CHUNK = 0x4E4F534A


def read_glb(path: Path) -> tuple[dict, list[tuple[int, bytes]]]:
    data = path.read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total != len(data):
        raise ValueError(f"{path} is not a valid glTF 2.0 binary.")

    chunks: list[tuple[int, bytes]] = []
    offset = 12
    document: dict | None = None
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        payload = data[offset + 8 : offset + 8 + length]
        offset += 8 + length
        if kind == JSON_CHUNK:
            document = json.loads(payload.decode("utf-8").rstrip("\x00 "))
        else:
            chunks.append((kind, payload))
    if document is None:
        raise ValueError("GLB does not contain a JSON chunk.")
    return document, chunks


def write_glb(path: Path, document: dict, chunks: list[tuple[int, bytes]]) -> None:
    raw_json = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    raw_json += b" " * ((4 - len(raw_json) % 4) % 4)
    packed = [(JSON_CHUNK, raw_json), *chunks]
    total = 12 + sum(8 + len(payload) for _, payload in packed)
    output = bytearray(struct.pack("<4sII", b"glTF", 2, total))
    for kind, payload in packed:
        output.extend(struct.pack("<II", len(payload), kind))
        output.extend(payload)
    path.write_bytes(output)


def set_transform(node: dict, *, translation=None, scale=None) -> None:
    if translation is not None:
        node["translation"] = translation
    if scale is not None:
        node["scale"] = scale


def rebuild(document: dict) -> None:
    nodes = {node.get("name"): node for node in document.get("nodes", [])}

    # Narrower skull and longer vertical crown eliminate the spherical/cartoon silhouette.
    set_transform(nodes["Head"], translation=[0, 1.82, 0.08], scale=[0.90, 1.05, 0.94])

    # Tall, narrow ears with a slightly tighter placement match the supplied turnaround.
    set_transform(nodes["Ear.L"], translation=[-0.88, 1.78, 0.04], scale=[0.72, 1.18, 0.82])
    set_transform(nodes["Ear.R"], translation=[0.88, 1.78, 0.04], scale=[0.72, 1.18, 0.82])
    set_transform(nodes["EarInner.L"], translation=[0, -0.02, -0.34], scale=[0.72, 0.94, 0.75])
    set_transform(nodes["EarInner.R"], translation=[0, -0.02, -0.34], scale=[0.72, 0.94, 0.75])

    # Sharpen the eye/brow mask and reduce the oversized cheek width.
    set_transform(nodes["Brow.L"], translation=[-0.61, 0.43, -0.94], scale=[0.92, 0.82, 0.80])
    set_transform(nodes["Brow.R"], translation=[0.61, 0.43, -0.94], scale=[0.92, 0.82, 0.80])
    set_transform(nodes["Eye.L"], translation=[-0.53, 0.04, -1.50], scale=[1.08, 0.72, 0.82])
    set_transform(nodes["Eye.R"], translation=[0.53, 0.04, -1.50], scale=[1.08, 0.72, 0.82])
    set_transform(nodes["Cheek.L"], translation=[-0.91, -0.48, -0.96], scale=[0.83, 1.02, 0.86])
    set_transform(nodes["Cheek.R"], translation=[0.91, -0.48, -0.96], scale=[0.83, 1.02, 0.86])
    set_transform(nodes["Mane.L"], translation=[-1.31, -0.60, -0.04], scale=[0.86, 1.10, 0.92])
    set_transform(nodes["Mane.R"], translation=[1.31, -0.60, -0.04], scale=[0.86, 1.10, 0.92])

    # Lengthen and narrow the muzzle. The old short, broad muzzle caused the bulldog-like face.
    set_transform(nodes["UpperMuzzle"], translation=[0, -0.80, -1.27], scale=[0.78, 0.82, 1.48])
    set_transform(nodes["Nose"], translation=[0, -0.70, -0.57], scale=[0.66, 0.66, 0.72])
    set_transform(nodes["MouthInterior"], translation=[0, -1.50, -1.48], scale=[0.80, 0.70, 1.18])
    set_transform(nodes["Jaw"], translation=[0, -1.50, -1.39], scale=[0.80, 0.72, 1.24])
    set_transform(nodes["ChinCyan"], translation=[0, -0.27, -0.43], scale=[0.78, 0.80, 1.0])

    # Pull the cyan circuitry onto the new armor silhouette.
    set_transform(nodes["ForeheadCircuit"], translation=[0, 0.78, -1.51], scale=[0.82, 1.0, 0.82])
    set_transform(nodes["CheekCircuit.L"], translation=[-1.00, -0.46, -1.16], scale=[0.82, 0.92, 0.82])
    set_transform(nodes["CheekCircuit.R"], translation=[1.00, -0.46, -1.16], scale=[0.82, 0.92, 0.82])

    # Broader layered bust, with less rounded shoulder mass.
    set_transform(nodes["Shoulder.L"], translation=[-1.42, -2.75, 0.28], scale=[1.08, 0.74, 0.90])
    set_transform(nodes["Shoulder.R"], translation=[1.42, -2.75, 0.28], scale=[1.08, 0.74, 0.90])
    set_transform(nodes["Chest"], translation=[0, -2.74, 0.28], scale=[0.98, 0.82, 0.92])

    material_values = {
        "Midnight_Navy": ([0.012, 0.028, 0.052, 1], 0.72, 0.38),
        "Gunmetal": ([0.055, 0.085, 0.125, 1], 0.76, 0.40),
        "Cool_Silver": ([0.27, 0.34, 0.42, 1], 0.82, 0.34),
        "Muzzle_Black": ([0.004, 0.007, 0.012, 1], 0.24, 0.50),
    }
    for material in document.get("materials", []):
        values = material_values.get(material.get("name"))
        if values:
            color, metallic, roughness = values
            pbr = material.setdefault("pbrMetallicRoughness", {})
            pbr["baseColorFactor"] = color
            pbr["metallicFactor"] = metallic
            pbr["roughnessFactor"] = roughness
        if material.get("name") == "Cyan_Emission":
            material["emissiveFactor"] = [0.0, 0.62, 0.82]
            material.setdefault("extensions", {}).setdefault(
                "KHR_materials_emissive_strength", {}
            )["emissiveStrength"] = 2.1

    asset = document.setdefault("asset", {})
    asset["generator"] = "Wolforge proportion-correction pipeline v2"
    asset["copyright"] = "Wolforge original local-use project asset"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    document, chunks = read_glb(args.source)
    rebuild(document)
    write_glb(args.destination, document, chunks)
    print(f"Wrote {args.destination} ({args.destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
