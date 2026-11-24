"""
NetWeave local-rules v3 — overhead precision traffic-instrument treatment.

Blind-draft of an additional iteration. Same composition contract as v1 and v2
(orthographic studio plate, two shallow parallel lanes, nine discrete cell
positions per lane, four vehicles in the upper lane, vehicle D stationary at
cell 7). Same three hand-authored poses. Same 1600x1100 desktop and 800x1000
mobile resolutions. Same six PNG review frames.

Differences from v2:
  * The road plate is now a thin asphalt slab rather than a raised dark frame.
    The thick CNC chamfer that read as a keyboard tray in v2 is gone.
  * Cells are no longer raised CNC pockets. The nine positions per lane are
    marked by subtle perpendicular lane-edge ticks and a faint dotted center
    line. Countable, but no longer white "keycaps".
  * Vehicles are elongated low-profile bodies (length:width roughly 2.25:1)
    with four small wheel cylinders visible at the corners and a low roof
    panel. The cube-shaped keycap silhouette is gone.
  * Direction-of-travel geometry is reinforced with chevron arrows at each
    occupied cell and a wider approach arrow at the left edge of the upper
    lane, painted in the system teal accent.
  * Lane markings: solid edge lines on the curbs, dashed centerline, light
    perpendicular cell ticks. Materials are technical: matte asphalt,
    warm-cream paint, low-metallic vehicle paint.
  * Camera framing tightened further on both desktop and mobile so the road
    fills the frame with minimal blank margin.

Boundary unchanged: hand-authored explanatory local-spacing study, not
telemetry and not a faithful simulator trace.

Provenance: original procedural geometry; no third-party inputs; no license
grant asserted. Reproduces with seed=0 (deterministic).
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


# ---------- CLI -------------------------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', required=True,
                    help='Output directory; v3 subdirectory preferred.')
parser.add_argument('--save-scene',
                    help='Optional .blend path to save the desktop state-1 scene.')
parser.add_argument('--state', type=int, choices=[1, 2, 3], required=True)
parser.add_argument('--suffix', default='-v3',
                    help='Filename suffix for additive naming (default: -v3).')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])

out = Path(args.output_dir).resolve()
out.mkdir(parents=True, exist_ok=True)


# ---------- Reset scene -----------------------------------------------------

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


# ---------- Materials -------------------------------------------------------

def principled(name, color, *, roughness=0.45, metallic=0.0,
               anisotropic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    if 'Anisotropic' in bsdf.inputs:
        bsdf.inputs['Anisotropic'].default_value = anisotropic
    bsdf.inputs['Specular IOR Level'].default_value = 0.55
    return mat


# Warm paper ground, same family as v1/v2.
paper = principled('Studio paper',     (0.74, 0.69, 0.58), roughness=0.85)

# Matte asphalt road slab — flat, technical, slightly cool.
asphalt = principled('Asphalt slab', (0.078, 0.084, 0.092),
                     roughness=0.78, metallic=0.05)

# Warm-cream road paint for curbs, lane lines, cell ticks, and chevrons.
paint = principled('Road paint',   (0.86, 0.82, 0.71), roughness=0.62)

# Slightly darker amber-cream for the dashed centerline so it reads as the
# centerline convention without resorting to bright yellow.
centerline = principled('Centerline paint', (0.78, 0.70, 0.50), roughness=0.65)

# System accent — teal — applied only to approach chevrons.
teal_pin = principled('Teal accent', (0.32, 0.61, 0.59),
                      roughness=0.45, metallic=0.25)

# Vehicle paints — low-metallic, satin-finish body panels.
cool = principled('Follower mineral blue', (0.16, 0.37, 0.44),
                  roughness=0.32, metallic=0.35)

amber = principled('Selected follower amber', (0.95, 0.39, 0.065),
                   roughness=0.30, metallic=0.30)

lead = principled('Lead dark steel', (0.20, 0.23, 0.27),
                  roughness=0.32, metallic=0.55)

# Glass — used for the windshield hint on the front of each vehicle body.
glass = principled('Glass panel', (0.10, 0.13, 0.16),
                   roughness=0.10, metallic=0.0)

# Wheels — near-black rubber.
rubber = principled('Rubber tyre', (0.045, 0.045, 0.048),
                    roughness=0.85, metallic=0.0)


# ---------- Helpers ---------------------------------------------------------

def box(name, location, scale, mat, *, bevel=0.04, bevel_segments=3,
        apply_scale=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    if apply_scale:
        bpy.ops.object.transform_apply(location=False, rotation=False,
                                       scale=True)
    obj.data.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new('Precision chamfer', 'BEVEL')
        mod.width = bevel
        mod.segments = bevel_segments
        mod.affect = 'EDGES'
    wn = obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    wn.weight = 50
    wn.keep_sharp = True
    return obj


def cylinder(name, location, radius, depth, mat, *, rotation=(0, 0, 0),
             bevel=0.012):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                        location=location, vertices=24)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    obj.data.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new('Tyre chamfer', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.affect = 'EDGES'
    wn = obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    wn.weight = 50
    wn.keep_sharp = True
    return obj


def chevron(name, location, length, width, mat, *, depth=0.012,
            z=0.282):
    """A flat >-shaped chevron built from two thin tapered boxes.

    Built as a V-shape rather than a single extruded geometry so the arms stay
    thin and crisp at small render scales without requiring extra bevels.
    """
    # Each arm: a thin rectangle rotated to form half the chevron.
    arm_len = length * 0.55
    # Right arm (pointing forward-right).
    bpy.ops.mesh.primitive_cube_add(size=1, location=(
        location[0] + length * 0.18,
        location[1] + width * 0.22,
        z,
    ))
    obj_r = bpy.context.object
    obj_r.name = name + '_R'
    obj_r.dimensions = (arm_len, width * 0.45, depth)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj_r.rotation_euler = (0, 0, 0.55)
    obj_r.data.materials.append(mat)
    wn_r = obj_r.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    wn_r.weight = 50
    wn_r.keep_sharp = True

    # Left arm (pointing forward-left).
    bpy.ops.mesh.primitive_cube_add(size=1, location=(
        location[0] + length * 0.18,
        location[1] - width * 0.22,
        z,
    ))
    obj_l = bpy.context.object
    obj_l.name = name + '_L'
    obj_l.dimensions = (arm_len, width * 0.45, depth)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj_l.rotation_euler = (0, 0, -0.55)
    obj_l.data.materials.append(mat)
    wn_l = obj_l.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    wn_l.weight = 50
    wn_l.keep_sharp = True


# ---------- Ground ----------------------------------------------------------

box('Paper ground', (0, 0, -0.35), (200, 200, 0.10), paper, bevel=0.02,
    bevel_segments=2)


# ---------- Road plate (thin asphalt slab) ----------------------------------

# v2 was a thick chamfered slab; v3 is a thin flush asphalt surface. The
# reduced depth and chamfer make it read as a road, not a tray.
box('RoadSlab', (0, 0, -0.04), (11.50, 3.50, 0.06), asphalt, bevel=0.03,
    bevel_segments=2)


# ---------- Lane edge curbs (top and bottom) --------------------------------

# Solid cream curbs on the top and bottom edges of the road — the lane
# boundary lines. Slightly raised above the asphalt so they catch a sliver of
# light.
for y, sign in ((1.74, 1), (-1.74, -1)):
    box(f'Curb_{"T" if sign > 0 else "B"}',
        (0, y, 0.005),
        (11.40, 0.06, 0.012), paint, bevel=0.003, bevel_segments=2)


# ---------- Dashed centerline between lanes ---------------------------------

# Nine dashed segments between the two lanes. The dashes alternate with gaps
# of equal length so the lane reads as a two-way road.
dash_length = 0.55
gap_length = 0.40
running = -((9 * dash_length + 8 * gap_length) / 2)
for i in range(9):
    cx = running + dash_length / 2
    box(f'CenterDash_{i:02}',
        (cx, 0.0, 0.005),
        (dash_length, 0.045, 0.010), centerline, bevel=0.002,
        bevel_segments=2)
    running += dash_length + gap_length


# ---------- Cell markings (subtle perpendicular ticks) ----------------------

# A thin perpendicular tick at each of the nine cell positions per lane.
# Tick straddles the lane width so the position is countable without reading
# as a keycap.
for lane in range(2):
    lane_y = (lane - 0.5) * 1.15
    for cell in range(9):
        cx = cell - 4
        # Outer (curb-side) edge tick — cream.
        box(f'CellTick_L{lane}_{cell:02}_Outer',
            (cx, lane_y + 0.46, 0.005),
            (0.04, 0.06, 0.008), paint, bevel=0.001, bevel_segments=2)
        # Inner (centerline-side) edge tick — cream.
        box(f'CellTick_L{lane}_{cell:02}_Inner',
            (cx, lane_y - 0.46, 0.005),
            (0.04, 0.06, 0.008), paint, bevel=0.001, bevel_segments=2)
        # Small perpendicular short line across the lane — pale, very thin.
        # Only on the upper lane to avoid cluttering the lower (empty) lane.
        if lane == 0:
            box(f'CellTick_L{lane}_{cell:02}_Mid',
                (cx, lane_y + 0.16, 0.005),
                (0.03, 0.30, 0.006), paint, bevel=0.001, bevel_segments=2)


# ---------- Approach chevrons (left edge of upper lane) ---------------------

# A wider chevron at the left edge of the upper lane establishes direction
# without baked text. Two small chevrons at cells 0 and 1.
for cell in (0, 1):
    cx = cell - 4
    chevron(f'ApproachChev_{cell}',
            (cx - 0.2, -0.575),
            length=0.55 if cell == 0 else 0.40,
            width=0.40,
            mat=teal_pin,
            depth=0.014, z=0.012)


# ---------- Vehicles (elongated low-profile bodies) ------------------------

poses = [[0, 2, 4, 7], [1, 3, 5, 7], [2, 4, 6, 7]]

LANE_Y = -0.575
BODY_LEN = 1.40
BODY_WID = 0.62
BODY_HEIGHT = 0.24

for idx, cell in enumerate(poses[args.state - 1]):
    letter = chr(65 + idx)
    x = cell - 4
    is_lead = idx == 3
    is_selected = idx == 2

    if is_lead:
        body_mat = lead
    elif is_selected:
        body_mat = amber
    else:
        body_mat = cool

    # Main body — long, low-profile slab. Round chamfer reads as a vehicle
    # silhouette rather than a cube. Front (right) end slightly narrower by
    # pulling the front wheels in.
    box(f'Vehicle_{letter}_Body',
        (x, LANE_Y, 0.16),
        (BODY_LEN, BODY_WID, BODY_HEIGHT),
        body_mat,
        bevel=0.07, bevel_segments=4)

    # Lower body skirt — slightly wider, very thin, dark steel only on lead.
    if is_lead:
        box(f'Vehicle_{letter}_Skirt',
            (x, LANE_Y, 0.08),
            (BODY_LEN + 0.10, BODY_WID + 0.06, 0.04),
            lead,
            bevel=0.04, bevel_segments=3)

    # Roof / cabin panel — low, slightly shorter than the body, positioned
    # toward the rear so the front has a hood.
    box(f'Vehicle_{letter}_Roof',
        (x - 0.12, LANE_Y, 0.16 + BODY_HEIGHT / 2 + 0.04),
        (0.80, BODY_WID - 0.06, 0.12),
        body_mat,
        bevel=0.025, bevel_segments=3)

    # Windshield hint — small dark glass panel at the front of the roof.
    box(f'Vehicle_{letter}_Glass',
        (x + 0.28, LANE_Y, 0.16 + BODY_HEIGHT / 2 + 0.115),
        (0.14, BODY_WID - 0.10, 0.04),
        glass,
        bevel=0.008, bevel_segments=2)

    # Front bumper accent — a thin coloured stripe at the very front so the
    # direction of travel is unambiguous. Width slightly under body width.
    box(f'Vehicle_{letter}_Bumper',
        (x + BODY_LEN / 2 + 0.01, LANE_Y, 0.14),
        (0.03, BODY_WID - 0.04, 0.04),
        body_mat,
        bevel=0.006, bevel_segments=2)

    # Wheels — four cylinders, oriented so the round face points sideways.
    # Wheel positions are slightly inset toward the body ends.
    wheel_offset_x = 0.45
    wheel_offset_y = BODY_WID / 2 - 0.02
    for wname, dx, dy in (
        ('FL', +wheel_offset_x, +wheel_offset_y),
        ('FR', +wheel_offset_x, -wheel_offset_y),
        ('RL', -wheel_offset_x, +wheel_offset_y),
        ('RR', -wheel_offset_x, -wheel_offset_y),
    ):
        cylinder(
            f'Vehicle_{letter}_W_{wname}',
            (x + dx, LANE_Y + dy, 0.10),
            radius=0.13,
            depth=0.10,
            mat=rubber,
            rotation=(0, 0, 1.5708),  # 90deg so the round face points along Y
            bevel=0.012,
        )


# ---------- Cell directional chevrons under occupied cells -------------------

# A small cream chevron under each occupied cell of the upper lane reinforces
# the right-pointing direction of travel. Only painted on the upper lane to
# keep the empty lane quiet.
for cell in poses[args.state - 1]:
    cx = cell - 4
    chevron(f'CellChev_{cell}',
            (cx + 0.05, -0.18),
            length=0.30,
            width=0.18,
            mat=paint,
            depth=0.008, z=0.012)


# ---------- Lighting --------------------------------------------------------

# Cool key from upper-left, warm fill from lower-right, subtle rim on right.
for name, loc, energy, size in [
    ('Key_Area',  ( 1.4, -5.2, 9.5), 1750, 7.5),
    ('Fill_Area', (-6.0,  3.0, 6.0),  900, 6.5),
    ('Rim_Area',  ( 4.0,  4.5, 5.5),  450, 5.0),
]:
    bpy.ops.object.light_add(type='AREA', location=loc)
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.energy = energy
    lamp.data.shape = 'DISK'
    lamp.data.size = size
    lamp.rotation_euler = (Vector((0, 0, 0)) - lamp.location).to_track_quat('-Z', 'Y').to_euler()


# ---------- Render setup ----------------------------------------------------

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 28
scene.cycles.use_denoising = True
scene.world.color = (0.30, 0.30, 0.30)
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene['evidence_boundary'] = 'Original illustrative artwork, not recorded NetWeave output'
scene['state'] = args.state
scene['seed'] = 0
scene['asset_version'] = 'v3-overhead-traffic-instrument'


# ---------- Cameras ---------------------------------------------------------

# Desktop: slightly tighter than v2; oblique angle that keeps every occupied
# cell countable. Mobile: higher camera and tighter ortho so the road fills
# the frame with minimal blank margin, addressing v2's top/bottom whitespace.
for kind, loc, ortho, dims in [
    ('desktop', (8.2, -11.0, 13.5), 10.2, (1600, 1100)),
    # Give the portrait camera enough longitudinal room for the first and
    # last vehicles; the previous 9.5 scale clipped the left follower.
    ('mobile',  (0.0,  -4.5, 21.0), 12.8, ( 800, 1000)),
]:
    bpy.ops.object.camera_add(location=loc)
    camera = bpy.context.object
    camera.name = 'Camera_' + kind.title()
    camera.rotation_euler = (Vector((0, 0, 0.10)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = ortho
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = dims
    scene.render.filepath = str(out / f'{kind}-{args.state:02}{args.suffix}.png')
    if args.save_scene and kind == 'desktop':
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.save_scene).resolve()))
    bpy.ops.render.render(write_still=True)


# ---------- State provenance JSON -------------------------------------------

(out / f'state-{args.state:02}{args.suffix}.json').write_text(json.dumps({
    'state': args.state,
    'lane_0': poses[args.state - 1],
    'lane_1': [],
    'seed': 0,
    'asset_version': 'v3-overhead-traffic-instrument',
    'boundary': scene['evidence_boundary'],
    'poses_source': 'hand-authored, identical to v1/v2; visual treatment only differs',
    'notes': 'Plate flattened to thin asphalt slab; cells demoted from raised CNC pockets to subtle perpendicular ticks; vehicles elongated to ~2.25:1 length:width with four visible wheels and a windshield hint; chevrons painted on the road surface to indicate direction',
}, indent=2))
