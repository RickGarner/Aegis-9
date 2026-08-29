#!/usr/bin/env python3
"""Extract a WebView-ready cyber-lupine portrait bust from the supplied full character."""

from __future__ import annotations

import argparse
import json
import mimetypes
import struct
from pathlib import Path

import numpy as np

COMPONENTS = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
COUNTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


class Builder:
    def __init__(self) -> None:
        self.binary = bytearray()
        self.views: list[dict] = []
        self.accessors: list[dict] = []

    def align(self, byte: int = 0) -> None:
        self.binary.extend(bytes([byte]) * ((4 - len(self.binary) % 4) % 4))

    def add_array(self, values: np.ndarray, component_type: int, kind: str, target: int) -> int:
        self.align()
        values = np.ascontiguousarray(values.astype(COMPONENTS[component_type], copy=False))
        offset = len(self.binary)
        payload = values.tobytes()
        self.binary.extend(payload)
        view_index = len(self.views)
        self.views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(payload), "target": target})
        accessor = {
            "bufferView": view_index,
            "componentType": component_type,
            "count": len(values),
            "type": kind,
        }
        if kind == "VEC3" and component_type == 5126:
            accessor["min"] = values.min(axis=0).astype(float).tolist()
            accessor["max"] = values.max(axis=0).astype(float).tolist()
        accessor_index = len(self.accessors)
        self.accessors.append(accessor)
        return accessor_index

    def add_image(self, payload: bytes, mime_type: str) -> dict:
        self.align()
        offset = len(self.binary)
        self.binary.extend(payload)
        view_index = len(self.views)
        self.views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(payload)})
        return {"bufferView": view_index, "mimeType": mime_type}


def read_accessor(document: dict, source: bytes, index: int) -> np.ndarray:
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    dtype = COMPONENTS[accessor["componentType"]]
    width = COUNTS[accessor["type"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return np.frombuffer(source, dtype=dtype, count=accessor["count"] * width, offset=offset).reshape(-1, width)


def write_glb(path: Path, document: dict, binary: bytearray) -> None:
    while len(binary) % 4:
        binary.append(0)
    raw_json = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    raw_json += b" " * ((4 - len(raw_json) % 4) % 4)
    total = 12 + 8 + len(raw_json) + 8 + len(binary)
    output = bytearray(struct.pack("<4sII", b"glTF", 2, total))
    output.extend(struct.pack("<II", len(raw_json), JSON_CHUNK))
    output.extend(raw_json)
    output.extend(struct.pack("<II", len(binary), BIN_CHUNK))
    output.extend(binary)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Source scene.gltf")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--minimum-y", type=float, default=0.28)
    parser.add_argument("--maximum-x", type=float, default=0.26)
    args = parser.parse_args()

    root = args.source.parent
    source_document = json.loads(args.source.read_text(encoding="utf-8"))
    source_buffer = (root / source_document["buffers"][0]["uri"]).read_bytes()
    builder = Builder()
    meshes: list[dict] = []
    nodes: list[dict] = []
    total_triangles = 0

    for mesh_index, source_mesh in enumerate(source_document.get("meshes", [])):
        primitive = source_mesh["primitives"][0]
        positions = read_accessor(source_document, source_buffer, primitive["attributes"]["POSITION"]).astype(np.float32)
        normals = read_accessor(source_document, source_buffer, primitive["attributes"]["NORMAL"]).astype(np.float32)
        texcoords = read_accessor(source_document, source_buffer, primitive["attributes"]["TEXCOORD_0"]).astype(np.float32)
        indices = read_accessor(source_document, source_buffer, primitive["indices"]).reshape(-1).astype(np.uint32)
        triangles = indices.reshape(-1, 3)

        triangle_positions = positions[triangles]
        keep = (
            (triangle_positions[:, :, 1].min(axis=1) >= args.minimum_y)
            & (np.abs(triangle_positions[:, :, 0]).max(axis=1) <= args.maximum_x)
        )
        selected = triangles[keep]
        if not len(selected):
            continue

        used, inverse = np.unique(selected.reshape(-1), return_inverse=True)
        compact_indices = inverse.reshape(-1, 3).astype(np.uint32)
        total_triangles += len(compact_indices)
        attributes = {
            "POSITION": builder.add_array(positions[used], 5126, "VEC3", 34962),
            "NORMAL": builder.add_array(normals[used], 5126, "VEC3", 34962),
            "TEXCOORD_0": builder.add_array(texcoords[used], 5126, "VEC2", 34962),
        }
        index_accessor = builder.add_array(compact_indices.reshape(-1, 1), 5125, "SCALAR", 34963)
        output_mesh_index = len(meshes)
        meshes.append({
            "name": f"CyberLupineBust_{mesh_index}",
            "primitives": [{"attributes": attributes, "indices": index_accessor, "material": 0, "mode": 4}],
        })
        nodes.append({"name": f"BustSection_{mesh_index}", "mesh": output_mesh_index})

    image_source = source_document["images"][0]["uri"]
    image_payload = (root / image_source).read_bytes()
    image = builder.add_image(image_payload, mimetypes.guess_type(image_source)[0] or "image/jpeg")
    materials = source_document.get("materials", [])
    if materials:
        material = materials[0]
        material["name"] = "Cyber_Lupine_PBR"
        pbr = material.setdefault("pbrMetallicRoughness", {})
        pbr["metallicFactor"] = 0.12
        pbr["roughnessFactor"] = 0.62

    document = {
        "asset": {
            "version": "2.0",
            "generator": "Jarvis cyber-lupine portrait extractor",
            "extras": source_document.get("asset", {}).get("extras", {}),
        },
        "scene": 0,
        "scenes": [{"name": "JarvisCyberLupineBust", "nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "textures": source_document.get("textures", []),
        "samplers": source_document.get("samplers", []),
        "images": [image],
        "buffers": [{"byteLength": len(builder.binary)}],
        "bufferViews": builder.views,
        "accessors": builder.accessors,
    }
    write_glb(args.destination, document, builder.binary)
    print(f"Wrote {args.destination}")
    print(f"Portrait meshes: {len(meshes)}")
    print(f"Portrait triangles: {total_triangles:,}")
    print(f"File size: {args.destination.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
