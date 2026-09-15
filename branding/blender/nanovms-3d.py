# NanoVMS 3D Logo Generator (Blender 3.x / 4.x)
# Run: blender --background --python nanovms-3d.py
# Output: branding/blender/nanovms-3d.png (512x512)

import bpy
import math

# ── Clear scene ──────────────────────────────────────────────
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

for c in bpy.data.collections:
    bpy.data.collections.remove(c)

for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)

# ── Materials ────────────────────────────────────────────────
def make_mat(name, color, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    if emission > 0:
        bsdf.inputs["Emission Strength"].default_value = emission
        bsdf.inputs["Emission Color"].default_value = color
    return mat

mat_bg      = make_mat("bg",      (0.04, 0.055, 0.15, 1))
mat_cyan    = make_mat("cyan",    (0.0, 0.83, 1.0, 1), emission=2.0)
mat_purple  = make_mat("purple",  (0.48, 0.18, 0.97, 1), emission=1.5)
mat_pink    = make_mat("pink",    (1.0, 0.0, 0.5, 1), emission=1.5)

# ── Background plane ─────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, -0.1))
bg = bpy.context.active_object
bg.name = "background"
bg.data.materials.append(mat_bg)

# ── Outer hexagon (VM shell) ─────────────────────────────────
verts = []
edges = []
r_outer = 2.0
for i in range(6):
    angle = math.radians(60 * i + 30)
    verts.append((r_outer * math.cos(angle), r_outer * math.sin(angle), 0))
    edges.append((i, (i + 1) % 6))

mesh = bpy.data.meshes.new("hex_outer")
mesh.from_pydata(verts, edges, [])
mesh.update()

hex_outer = bpy.data.objects.new("hex_outer", mesh)
bpy.context.collection.objects.link(hex_outer)

# Convert to curve for thickness
bpy.context.view_layer.objects.active = hex_outer
hex_outer.select_set(True)
bpy.ops.object.convert(target='CURVE')
hex_outer.data.bevel_depth = 0.08
hex_outer.data.bevel_resolution = 4
hex_outer.data.materials.append(mat_cyan)

# ── Inner hexagon (sandbox layer) ────────────────────────────
verts2 = []
edges2 = []
r_inner = 1.3
for i in range(6):
    angle = math.radians(60 * i + 30)
    verts2.append((r_inner * math.cos(angle), r_inner * math.sin(angle), 0))
    edges2.append((i, (i + 1) % 6))

mesh2 = bpy.data.meshes.new("hex_inner")
mesh2.from_pydata(verts2, edges2, [])
mesh2.update()

hex_inner = bpy.data.objects.new("hex_inner", mesh2)
bpy.context.collection.objects.link(hex_inner)
bpy.context.view_layer.objects.active = hex_inner
hex_inner.select_set(True)
bpy.ops.object.convert(target='CURVE')
hex_inner.data.bevel_depth = 0.05
hex_inner.data.bevel_resolution = 4
hex_inner.data.materials.append(mat_purple)

# ── Center sphere (core) ─────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(0, 0, 0))
core = bpy.context.active_object
core.name = "core"
core.data.materials.append(mat_pink)

# ── Tier dots on vertices ────────────────────────────────────
colors = [mat_cyan, mat_purple, mat_pink]
for i in range(6):
    angle = math.radians(60 * i + 30)
    x = r_outer * math.cos(angle)
    y = r_outer * math.sin(angle)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(x, y, 0))
    dot = bpy.context.active_object
    dot.name = f"tier_{i}"
    dot.data.materials.append(colors[i % 3])

# ── Camera ───────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(0, -5, 3), rotation=(math.radians(60), 0, 0))
cam = bpy.context.active_object
cam.name = "camera"
bpy.context.scene.camera = cam

# ── Lighting ─────────────────────────────────────────────────
bpy.ops.object.light_add(type='AREA', location=(3, -3, 4))
key = bpy.context.active_object
key.name = "key_light"
key.data.energy = 50
key.data.color = (0.0, 0.83, 1.0)

bpy.ops.object.light_add(type='AREA', location=(-3, -2, 3))
fill = bpy.context.active_object
fill.name = "fill_light"
fill.data.energy = 20
fill.data.color = (0.48, 0.18, 0.97)

bpy.ops.object.light_add(type='POINT', location=(0, 0, 2))
rim = bpy.context.active_object
rim.name = "rim_light"
rim.data.energy = 30
rim.data.color = (1.0, 0.0, 0.5)

# ── Render settings ──────────────────────────────────────────
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'

# ── Output ───────────────────────────────────────────────────
import os
output_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(output_dir, "nanovms-3d.png")
scene.render.filepath = output_path

bpy.ops.render.render(write_still=True)
print(f"Rendered: {output_path}")
