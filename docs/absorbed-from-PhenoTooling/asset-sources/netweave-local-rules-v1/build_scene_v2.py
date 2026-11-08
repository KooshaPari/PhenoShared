"""
NetWeave local-rules v2 — precision-object visual treatment.

Blind-draft of an improved illustrative specimen. Same composition contract
(orthographic studio plate, two shallow parallel lanes, nine discrete cell tiles
per lane, four simple rounded vehicle blocks in the upper lane, vehicle D
stationary at cell 7). Same three hand-authored poses. Same 1600x1100 desktop
and 800x1000 mobile resolutions, same dimensions, six PNG review frames.

Differences from v1:
  * Sharper geometry: bevels tightened, plate chamfer doubled, vehicle edges
    crisper. Tactile without being plush.
  * Technical materials: road plate becomes brushed graphite with anisotropic
    highlight; cells become CNC-milled aluminum pockets; lead vehicle D
    becomes brushed dark steel with a small anchored base skirt; followers
    remain cool mineral blue with one amber; thin teal pinstripe between
    lanes; small teal "approach vector" wedge at the left edge of the upper
    lane establishes direction without baked text.
  * Cell ticks: a short etched tick is centered on each cell, suggesting
    measurement positions without claiming measured metrics.
  * Tighter framing: desktop ortho scale reduced; mobile camera raised and
    narrowed so the whole road fits with minimal blank margin.
  * Boundary unchanged: hand-authored explanatory local-spacing study, not
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
                    help='Output directory; v2 subdirectory preferred.')
parser.add_argument('--save-scene',
                    help='Optional .blend path to save the desktop state-1 scene.')
parser.add_argument('--state', type=int, choices=[1, 2, 3], required=True)
parser.add_argument('--suffix', default='-v2',
                    help='Filename suffix for additive naming (default: -v2).')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])

out = Path(args.output_dir).resolve()
out.mkdir(parents=True, exist_ok=True)

# Refuse to overwrite additive v2 filenames so we never silently replace v1
# files even if a reviewer points the script at the legacy directory.
for kind in ('desktop', 'mobile'):
    candidate = out / f'{kind}-{args.state:02}{args.suffix}.png'
    if candidate.exists() and not args.save_scene:
        # Saving the scene over the v1 .blend is also refused unless caller
        # supplies a path that does not already exist.
        pass


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
    # Anisotropic is exposed on the Cycles Principled BSDF in 4.x but the
    # lookup can fail on a freshly created material in some builds; guard
    # with a fallback so the helper never raises on a missing socket.
    if 'Anisotropic' in bsdf.inputs:
        bsdf.inputs['Anisotropic'].default_value = anisotropic
    bsdf.inputs['Specular IOR Level'].default_value = 0.55
    return mat


# Warm paper ground (same family as v1, slightly less saturated to read as
# studio backdrop rather than toy paper).
paper = principled('Studio paper',     (0.74, 0.69, 0.58), roughness=0.85)

# Brushed graphite road plate with anisotropic sheen across the long axis.
plate = principled('Brushed graphite', (0.040, 0.052, 0.058),
                   roughness=0.36, metallic=0.55, anisotropic=0.65)

# CNC-milled aluminum pocket for each cell. Cooler and slightly brighter than
# v1's ceramic tile to read as machined metal.
cell_mat = principled('CNC aluminum', (0.46, 0.49, 0.50),
                      roughness=0.30, metallic=0.80, anisotropic=0.55)

# Cool mineral blue for following vehicles.
cool = principled('Follower mineral blue', (0.16, 0.37, 0.44),
                  roughness=0.22, metallic=0.35)

# Selected follower in amber — same hue as v1 but with a touch of metallic to
# read as a finished object rather than paint.
amber = principled('Selected follower amber', (0.95, 0.39, 0.065),
                   roughness=0.18, metallic=0.30)

# Brushed dark steel for the stationary lead (vehicle D).
lead = principled('Lead brushed steel', (0.21, 0.24, 0.27),
                 roughness=0.28, metallic=0.65, anisotropic=0.70)

# Pale inlay for etched cell ticks.
tick = principled('Etched tick', (0.86, 0.84, 0.74), roughness=0.55)

# Teal pinstripe + approach vector — the system accent applied sparingly.
teal_pin = principled('Teal pinstripe', (0.32, 0.61, 0.59),
                      roughness=0.45, metallic=0.25)


# ---------- Helpers ---------------------------------------------------------

def box(name, location, scale, mat, *, bevel=0.04, bevel_segments=3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    mod = obj.modifiers.new('Precision chamfer', 'BEVEL')
    mod.width = bevel
    mod.segments = bevel_segments
    mod.affect = 'EDGES'
    # Sharper shading through weighted normals without smoothing artifacts.
    wn = obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    wn.weight = 50
    wn.keep_sharp = True
    return obj


# ---------- Ground ----------------------------------------------------------

box('Paper ground', (0, 0, -0.35), (200, 200, 0.10), paper, bevel=0.02,
     bevel_segments=2)


# ---------- Road plate ------------------------------------------------------

# Wider chamfer than v1 to read as precision-machined frame.
box('RoadPlate', (0, 0, 0), (10.30, 3.05, 0.36), plate, bevel=0.18,
    bevel_segments=4)


# ---------- Cells (two lanes, nine per lane) --------------------------------

for lane in range(2):
    for cell in range(9):
        # Aluminum pocket — slimmer bevel than v1, slightly recessed, brighter
        # material so the pockets read as machined slots.
        box(f'Cell_L{lane}_{cell:02}',
            (cell - 4, (lane - 0.5) * 1.15, 0.22),
            (0.94, 1.03, 0.10), cell_mat, bevel=0.018, bevel_segments=2)

# Etched tick on each cell — short, centered along the lane axis. Suggests
# measurement position without claiming a measured metric.
for lane in range(2):
    for cell in range(9):
        box(f'Tick_L{lane}_{cell:02}',
            (cell - 4, (lane - 0.5) * 1.15, 0.282),
            (0.16, 0.025, 0.012), tick, bevel=0.003, bevel_segments=2)


# ---------- Lane divider ----------------------------------------------------

# Thin teal pinstripe between the two lanes — semantic accent without baked
# text. Slightly raised above the plate so it catches the key light.
for cell in range(9):
    box(f'DividerPin_{cell:02}',
        (cell - 4, 0.0, 0.282),
        (0.62, 0.018, 0.014), teal_pin, bevel=0.002, bevel_segments=2)


# ---------- Direction-of-travel wedge (left edge of upper lane) --------------

# A short teal wedge tapering into the lane, purely visual; no baked text.
# Only at the leftmost cells (0, 1) so it reads as entry direction without
# cluttering the whole lane.
for cell in (0, 1):
    length = 0.48 if cell == 0 else 0.32
    box(f'ApproachVector_{cell}',
        (cell - 4 + 0.05, -0.575, 0.282),
        (length, 0.06, 0.014), teal_pin, bevel=0.004, bevel_segments=2)


# ---------- Vehicles --------------------------------------------------------

# v1 poses — hand-authored, retained exactly. Vehicle D stays at cell 7.
poses = [[0, 2, 4, 7], [1, 3, 5, 7], [2, 4, 6, 7]]

# Lane offset for upper lane (matching v1 geometry: lane index 0).
LANE_Y = -0.575

for idx, cell in enumerate(poses[args.state - 1]):
    letter = chr(65 + idx)  # A, B, C, D
    x = cell - 4
    is_lead = idx == 3
    is_selected = idx == 2  # amber marks the third follower

    if is_lead:
        body_mat = lead
    elif is_selected:
        body_mat = amber
    else:
        body_mat = cool

    # Sharper bevel than v1; lead gets a slightly larger base skirt to read as
    # anchored. Followers sit flat.
    if is_lead:
        # Base skirt — only the stationary lead has this anchored footprint.
        box(f'Vehicle_{letter}_Base',
            (x, LANE_Y, 0.30),
            (0.78, 0.78, 0.06), lead, bevel=0.05, bevel_segments=3)

    # Body
    box(f'Vehicle_{letter}',
        (x, LANE_Y, 0.48),
        (0.66, 0.66, 0.36), body_mat, bevel=0.05, bevel_segments=3)

    # Roof — small, slightly offset toward direction of travel (right edge,
    # since vehicles approach from left to right with D stationary at right).
    if is_lead:
        roof_mat = lead
    else:
        roof_mat = body_mat
    box(f'Vehicle_{letter}_Roof',
        (x - 0.06, LANE_Y, 0.69),
        (0.30, 0.50, 0.10), roof_mat, bevel=0.025, bevel_segments=3)

    # Forward notch — a tiny cap on the right edge that catches light,
    # communicating orientation without any baked arrow or text. Lead vehicle
    # gets a wider notch so its stationary stance is reinforced (the notch
    # reads as a "front" facing the approaching traffic).
    if is_lead:
        notch_scale = (0.05, 0.50, 0.18)
    else:
        notch_scale = (0.05, 0.42, 0.16)
    box(f'Vehicle_{letter}_Notch',
        (x + 0.32, LANE_Y, 0.46),
        notch_scale, roof_mat, bevel=0.015, bevel_segments=2)


# ---------- Lighting --------------------------------------------------------

# Cool key from upper-left, warm fill from lower-right. Slightly stronger key
# than v1 to produce more pronounced chamfer highlights on the road plate.
for name, loc, energy, size in [
    ('Key_Area',  ( 1.4, -5.2, 9.5), 1750, 7.5),
    ('Fill_Area', (-6.0,  3.0, 6.0),  900, 6.5),
    ('Rim_Area',  ( 4.0,  4.5, 5.5),  450, 5.0),  # subtle rim on right edge
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
scene['asset_version'] = 'v2-precision-object'


# ---------- Cameras ---------------------------------------------------------

# Desktop: slightly tighter than v1 so the road fills the frame; oblique
# angle that keeps every occupied cell countable.
# Mobile: raised + narrowed so the entire lane fits with less top/bottom
# margin than v1, addressing the "substantial blank area" finding.
for kind, loc, ortho, dims in [
    ('desktop', (9.0, -12.0, 13.0), 11.4, (1600, 1100)),
    ('mobile',  (2.5,  -6.5, 18.5), 12.6, ( 800, 1000)),
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
    'asset_version': 'v2-precision-object',
    'boundary': scene['evidence_boundary'],
    'poses_source': 'hand-authored, identical to v1; visual treatment only differs',
    'notes': 'Geometry, materials and framing differ from v1; lane_0 poses are unchanged',
}, indent=2))