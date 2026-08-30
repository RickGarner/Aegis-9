"""Create a lightweight, no-cost control rig for the Cyber Lupine head.

Run with Blender 5.2 or newer:
  blender --background --python scripts/rig-cyber-lupine-head.py -- \
    desktop/Jarvis.Desktop/Assets/Avatars/shared/cyber_lupine_head.glb \
    desktop/Jarvis.Desktop/Assets/Avatars/shared/cyber_lupine_head_rigged.glb

The generated file is selected by the current Jarvis avatar manifests. Rebuild
the application after generation so the updated GLB is copied to the output.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def arguments() -> tuple[Path, Path]:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) != 2:
        raise SystemExit("Expected input.glb and output.glb after --")
    return Path(args[0]).resolve(), Path(args[1]).resolve()


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def mesh_bounds(meshes: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    return Vector(map(min, zip(*points))), Vector(map(max, zip(*points)))


def add_bone(armature, name: str, head: Vector, tail: Vector, parent=None):
    bone = armature.edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    bone.parent = parent
    return bone


def make_armature(minimum: Vector, maximum: Vector) -> bpy.types.Object:
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    width = maximum.x - minimum.x
    depth = maximum.y - minimum.y
    data = bpy.data.armatures.new("JarvisCyberLupineRig")
    rig = bpy.data.objects.new("JarvisCyberLupineRig", data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    neck = add_bone(data, "Neck", Vector((center.x, center.y, minimum.z)), Vector((center.x, center.y, center.z)))
    head = add_bone(data, "Head", Vector((center.x, center.y, center.z)), Vector((center.x, center.y, maximum.z - height * 0.12)), neck)
    add_bone(data, "LowerSnout", Vector((center.x, minimum.y + depth * 0.24, center.z + height * 0.01)), Vector((center.x, minimum.y - depth * 0.04, center.z - height * 0.055)), head)
    add_bone(data, "Ear.L", Vector((center.x + width * 0.20, center.y, maximum.z - height * 0.33)), Vector((center.x + width * 0.31, center.y, maximum.z)), head)
    add_bone(data, "Ear.R", Vector((center.x - width * 0.20, center.y, maximum.z - height * 0.33)), Vector((center.x - width * 0.31, center.y, maximum.z)), head)
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    return rig


def weight_mesh(obj: bpy.types.Object, rig: bpy.types.Object, minimum: Vector, maximum: Vector) -> None:
    inverse = obj.matrix_world.inverted()
    height = maximum.z - minimum.z
    width = maximum.x - minimum.x
    depth = maximum.y - minimum.y
    center = (minimum + maximum) * 0.5
    groups = {name: obj.vertex_groups.new(name=name) for name in ("Neck", "Head", "LowerSnout", "Ear.L", "Ear.R")}
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        weights = {"Head": 1.0}
        if world.z < minimum.z + height * 0.25:
            neck_weight = min(1.0, (minimum.z + height * 0.25 - world.z) / (height * 0.18))
            weights = {"Head": 1.0 - neck_weight, "Neck": neck_weight}
        # Restrict speech deformation to the lower/front muzzle.  The previous
        # broad jaw mask included cheeks and neck plates and looked hinged.
        in_lower_muzzle = center.z - height * 0.12 < world.z < center.z + height * 0.035
        in_front_muzzle = world.y < minimum.y + depth * 0.31
        in_muzzle_width = abs(world.x - center.x) < width * 0.24
        if in_lower_muzzle and in_front_muzzle and in_muzzle_width:
            weights = {"Head": 0.28, "LowerSnout": 0.72}
        if world.z > maximum.z - height * 0.38 and abs(world.x - center.x) > width * 0.14:
            ear = "Ear.L" if world.x > center.x else "Ear.R"
            weights = {"Head": 0.08, ear: 0.92}
        for name, weight in weights.items():
            if weight > 0:
                groups[name].add([vertex.index], weight, "REPLACE")
    modifier = obj.modifiers.new("Jarvis Cyber Lupine Rig", "ARMATURE")
    modifier.object = rig
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()


def action(rig: bpy.types.Object, name: str, bone_name: str, axis: str, degrees: float, frame: int = 12) -> None:
    created = bpy.data.actions.new(name)
    slot = created.slots.new(id_type="OBJECT", name=rig.name)
    rig.animation_data_create()
    rig.animation_data.action = created
    rig.animation_data.action_slot = slot
    pose_bone = rig.pose.bones[bone_name]
    pose_bone.rotation_mode = "XYZ"
    index = "XYZ".index(axis)
    pose_bone.rotation_euler[index] = 0
    pose_bone.keyframe_insert("rotation_euler", index=index, frame=1)
    pose_bone.rotation_euler[index] = math.radians(degrees)
    pose_bone.keyframe_insert("rotation_euler", index=index, frame=frame)
    pose_bone.rotation_euler[index] = 0
    pose_bone.keyframe_insert("rotation_euler", index=index, frame=frame * 2)
    created.use_fake_user = True


def thinking_action(rig: bpy.types.Object) -> None:
    created = bpy.data.actions.new("Jarvis_Thinking")
    slot = created.slots.new(id_type="OBJECT", name=rig.name)
    rig.animation_data_create()
    rig.animation_data.action = created
    rig.animation_data.action_slot = slot
    for name, degrees in (("Ear.L", -5.5), ("Ear.R", 5.5)):
        bone = rig.pose.bones[name]
        bone.rotation_mode = "XYZ"
        bone.rotation_euler.y = 0
        bone.keyframe_insert("rotation_euler", index=1, frame=1)
        bone.rotation_euler.y = math.radians(degrees)
        bone.keyframe_insert("rotation_euler", index=1, frame=14)
        bone.rotation_euler.y = math.radians(-degrees * 0.35)
        bone.keyframe_insert("rotation_euler", index=1, frame=28)
        bone.rotation_euler.y = 0
        bone.keyframe_insert("rotation_euler", index=1, frame=42)
    created.use_fake_user = True


def isolate_eye_material(meshes: list[bpy.types.Object]) -> int:
    """Split yellow-textured eye faces into an emissive material for runtime pulsing."""
    assigned = 0
    image_pixels: dict[int, tuple[int, int, np.ndarray]] = {}
    material_images: dict[int, bpy.types.Image | None] = {}
    for obj in meshes:
        uv_layer = obj.data.uv_layers.active
        if uv_layer is None:
            continue
        source_slots = list(obj.data.materials)
        eye_slots: dict[int, int] = {}
        for polygon in obj.data.polygons:
            source_index = polygon.material_index
            if source_index >= len(source_slots) or source_slots[source_index] is None:
                continue
            material = source_slots[source_index]
            material_key = material.as_pointer()
            if material_key not in material_images:
                image = None
                if material.node_tree is not None:
                    for node in material.node_tree.nodes:
                        if node.type == "TEX_IMAGE" and node.image is not None:
                            image = node.image
                            break
                material_images[material_key] = image
            image = material_images[material_key]
            if image is None or image.size[0] == 0 or image.size[1] == 0:
                continue
            image_key = image.as_pointer()
            if image_key not in image_pixels:
                width, height = int(image.size[0]), int(image.size[1])
                pixels = np.empty(len(image.pixels), dtype=np.float32)
                image.pixels.foreach_get(pixels)
                image_pixels[image_key] = (width, height, pixels)
                print(f"Cached eye-analysis texture {image.name}: {width}x{height}")
            width, height, pixels = image_pixels[image_key]
            loops = [uv_layer.data[index].uv for index in polygon.loop_indices]
            if not loops:
                continue
            u = (sum(point.x for point in loops) / len(loops)) % 1.0
            v = (sum(point.y for point in loops) / len(loops)) % 1.0
            x = min(width - 1, int(u * width))
            y = min(height - 1, int(v * height))
            offset = (y * width + x) * 4
            r, g, b = float(pixels[offset]), float(pixels[offset + 1]), float(pixels[offset + 2])
            is_yellow = r > 0.25 and g > 0.16 and b < 0.12 and r > b * 2.2 and g > b * 1.8
            if not is_yellow:
                continue
            if source_index not in eye_slots:
                eye_material = material.copy()
                eye_material.name = "Jarvis_Eyes"
                if eye_material.node_tree is not None:
                    principled = next((node for node in eye_material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
                    if principled is not None:
                        emission = principled.inputs.get("Emission Color") or principled.inputs.get("Emission")
                        strength = principled.inputs.get("Emission Strength")
                        if emission is not None:
                            emission.default_value = (1.0, 0.55, 0.0, 1.0)
                        if strength is not None:
                            strength.default_value = 1.25
                obj.data.materials.append(eye_material)
                eye_slots[source_index] = len(obj.data.materials) - 1
            polygon.material_index = eye_slots[source_index]
            assigned += 1
    print(f"Isolated {assigned} yellow eye faces for speaking-state color animation")
    return assigned


def main() -> None:
    source, destination = arguments()
    if not source.is_file():
        raise SystemExit(f"Input model does not exist: {source}")
    reset_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise SystemExit("The GLB contains no mesh objects")
    minimum, maximum = mesh_bounds(meshes)
    isolate_eye_material(meshes)
    rig = make_armature(minimum, maximum)
    for mesh in meshes:
        weight_mesh(mesh, rig, minimum, maximum)
    action(rig, "Jarvis_Idle", "Head", "X", 0.6, 48)
    action(rig, "Jarvis_Listening", "Head", "Z", 1.2, 22)
    thinking_action(rig)
    action(rig, "Jarvis_Speaking", "LowerSnout", "X", 3.6, 4)
    action(rig, "Jarvis_EarAlert_L", "Ear.L", "Y", -3.0, 9)
    action(rig, "Jarvis_EarAlert_R", "Ear.R", "Y", 3.0, 9)
    rig.animation_data.action = None
    destination.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(destination),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=True,
        export_morph=True,
    )
    print(f"Created review candidate: {destination}")


if __name__ == "__main__":
    main()
