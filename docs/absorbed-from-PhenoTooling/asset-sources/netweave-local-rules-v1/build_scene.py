import argparse
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', required=True)
parser.add_argument('--save-scene')
parser.add_argument('--state', type=int, choices=[1, 2, 3], required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = Path(args.output_dir).resolve()
out.mkdir(parents=True, exist_ok=True)
for kind in ['desktop', 'mobile']:
    if (out / f'{kind}-{args.state:02}.png').exists():
        raise RuntimeError('Output exists; select a fresh output directory')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def material(name, color, metal=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = .42
    bsdf.inputs['Metallic'].default_value = metal
    return mat

paper = material('Warm paper', (.72, .67, .56))
plate = material('Ink graphite', (.047, .064, .068))
tile = material('Lane ceramic', (.29, .35, .34))
cool = material('Vehicles mineral blue', (.16, .37, .44), .25)
amber = material('Selected vehicle amber', (.95, .39, .065), .15)
line = material('Pale inlay', (.78, .75, .63))

def box(name, location, scale, mat, bevel=.05):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    mod = obj.modifiers.new('Machined edges', 'BEVEL')
    mod.width = bevel
    mod.segments = 4
    obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj

box('Paper ground', (0, 0, -.35), (200, 200, .1), paper)
box('RoadPlate', (0, 0, 0), (10.3, 3.05, .36), plate, .13)
for lane in range(2):
    for cell in range(9):
        box(f'Cell_L{lane}_{cell:02}', (cell-4, (lane-.5)*1.15, .23), (.94, 1.03, .12), tile, .025)
for cell in range(9):
    box(f'CenterInlay_{cell}', (cell-4, 0, .23), (.28, .035, .025), line, .005)
poses = [[0, 2, 4, 7], [1, 3, 5, 7], [2, 4, 6, 7]]
for idx, cell in enumerate(poses[args.state-1]):
    box(f'Vehicle_{chr(65+idx)}', (cell-4, -.575, .49), (.68, .68, .4), amber if idx == 2 else cool, .11)
    box(f'Vehicle_{chr(65+idx)}_Roof', (cell-4-.06, -.575, .72), (.31, .52, .1), plate, .04)
for name, loc, energy, size in [('Key_Area', (1, -5, 10), 1500, 8), ('Fill_Area', (-6, 3, 6), 850, 7)]:
    bpy.ops.object.light_add(type='AREA', location=loc)
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.energy = energy
    lamp.data.shape = 'DISK'
    lamp.data.size = size
    lamp.rotation_euler = (Vector((0, 0, 0))-lamp.location).to_track_quat('-Z', 'Y').to_euler()
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.world.color = (.3, .3, .3)
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene['evidence_boundary'] = 'Original illustrative artwork, not recorded NetWeave output'
scene['state'] = args.state
scene['seed'] = 0
for kind, loc, ortho, dims in [('desktop', (9, -12, 13), 13.6, (1600, 1100)), ('mobile', (3, -7, 17), 14.5, (800, 1000))]:
    bpy.ops.object.camera_add(location=loc)
    camera = bpy.context.object
    camera.name = 'Camera_' + kind.title()
    camera.rotation_euler = (Vector((0, 0, .1))-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = ortho
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = dims
    scene.render.filepath = str(out / f'{kind}-{args.state:02}.png')
    if args.save_scene and kind == 'desktop':
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.save_scene).resolve()))
    bpy.ops.render.render(write_still=True)
(out / f'state-{args.state:02}.json').write_text(json.dumps({'state': args.state, 'lane_0': poses[args.state-1], 'lane_1': [], 'seed': 0, 'boundary': scene['evidence_boundary']}, indent=2))
