#!/usr/bin/env python3
"""Run inside Blender, in a new headless process. Rebuild the kit's editable asset.
Status in this distribution: Python syntax checked, Blender execution NOT RUN.
Example via scripts/run_blender.py. Never run this against an unsaved interactive scene.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]

def point(v): return (v[0],-v[2],v[1]) # Canonical +Y-up to Blender +Z-up, right handed.
def material(part):
    m=bpy.data.materials.new(part['name']+'_PBR');m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*part['color'],1)
    p.inputs['Roughness'].default_value=part['roughness'];p.inputs['Metallic'].default_value=part['metallic']
    if part['name']=='Upper':
        noise=m.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=165
        noise.inputs['Detail'].default_value=2
        bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.012
        m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
        m['export_note']='Procedural micro-bump is native-only until baked to a normal map. Do not claim GLB material parity.'
    return m

def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def area(name,location,power,size,target=(0,0,.45)):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=location;aim(obj,target);return obj

def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--input',type=Path,default=ROOT/'assets/concept-trainer.json');ap.add_argument('--render',action='store_true');ap.add_argument('--samples',type=int,default=24);ap.add_argument('--resolution',type=int,default=1000);args=ap.parse_args(argv)
    if args.output.exists():raise FileExistsError('Refusing existing output directory: '+str(args.output))
    if not 1<=args.samples<=256 or not 128<=args.resolution<=4096:raise ValueError('samples/resolution outside bounded preview limits')
    data=json.loads(args.input.read_text(encoding='utf-8'));args.output.mkdir(parents=True)
    # This script is explicitly a NEW-scene constructor, not a scene mutation tool.
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;objects=[]
    for part in data['parts']:
        positions=part['positions'];vertices=[point(positions[i:i+3]) for i in range(0,len(positions),3)]
        indices=part['indices'];faces=[tuple(indices[i:i+3]) for i in range(0,len(indices),3)]
        mesh=bpy.data.meshes.new(part['name']+'_mesh');mesh.from_pydata(vertices,[],faces);mesh.validate();mesh.update()
        obj=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(obj);obj.data.materials.append(material(part))
        for polygon in mesh.polygons:polygon.use_smooth=True
        obj['explode']=part['explode'];obj['accent']=part['accent'];obj['canonical_axes']='+Y up, +X toe'
        objects.append(obj)
    # Export only semantic model nodes; never lights, floor, or camera in the delivery asset.
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(args.output/'trainer.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.16));floor=bpy.context.object;floor.name='STUDIO_FLOOR'
    floor_mat=material(dict(name='Studio',color=[.78,.82,.78],roughness=.82,metallic=0));floor.data.materials.append(floor_mat)
    world=bpy.data.worlds.new('Studio world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.72,.69,1);world.node_tree.nodes['Background'].inputs[1].default_value=.35;scene.world=world
    area('Key',(-3,-4,6),650,5);area('Rim',(2,3,4),850,3);area('Fill',(4,-1,3),300,4)
    camera_data=bpy.data.cameras.new('Review camera');camera=bpy.data.objects.new('Review camera',camera_data);bpy.context.collection.objects.link(camera);scene.camera=camera;camera_data.lens=58
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=args.samples;scene.cycles.use_denoising=True
    scene.render.resolution_x=args.resolution;scene.render.resolution_y=round(args.resolution*.72);scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=False
    # Use AgX where available; record actual transform. Browser tone mapping will differ.
    try:scene.view_settings.view_transform='AgX'
    except TypeError:pass
    views={'three-quarter':(3.8,-6.8,3.7),'profile':(.2,-7.5,1.8),'rear':(-5.0,4.8,3.4)}
    camera.location=views['three-quarter'];aim(camera,(0,0,.43))
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output/'trainer.blend'))
    rendered=[]
    if args.render:
        for name,location in views.items():
            camera.location=location;aim(camera,(0,0,.43));scene.render.filepath=str(args.output/(name+'.png'));bpy.ops.render.render(write_still=True);rendered.append(name+'.png')
    files=[p for p in args.output.iterdir() if p.is_file()]
    receipt=dict(status='BUILT',blender_version=bpy.app.version_string,source_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(),render_engine=scene.render.engine,device=scene.cycles.device,color_transform=scene.view_settings.view_transform,renders=rendered,procedural_textures_baked=False,assets=[dict(path=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files],warning='Build completion is not artistic approval, standards validation, or browser material parity.')
    (args.output/'build-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
if __name__=='__main__':main()
