#!/usr/bin/env python3
"""Build an original procedural trainer, browser mesh data and standards-format GLB.
Python standard library only. No downloads, brands, textures or external model inputs.
Geometry is deliberately a concept/iteration seed, not a production scan of footwear.
"""
from __future__ import annotations
import argparse, array, hashlib, json, math, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Vec = tuple[float, float, float]
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a):
    n=math.sqrt(sum(x*x for x in a))
    return tuple(x/n for x in a) if n>1e-12 else (0.,1.,0.)
def make(name, positions, triangles, color, roughness=.55, metallic=0., explode=(0.,0.,0.), accent=False):
    normals=[[0.,0.,0.] for _ in positions]
    for ia,ib,ic in triangles:
        n=cross(sub(positions[ib],positions[ia]), sub(positions[ic],positions[ia]))
        for i in (ia,ib,ic):
            for j in range(3): normals[i][j]+=n[j]
    return dict(name=name,positions=[round(v,6) for p in positions for v in p],
                normals=[round(v,6) for n in normals for v in norm(n)],
                indices=[i for t in triangles for i in t],color=color,
                roughness=roughness,metallic=metallic,explode=list(explode),accent=accent)

def loft(name,sections,color,roughness=.55,metallic=0.,explode=(0.,0.,0.),accent=False,steps=40,exponent=1.):
    """Sections are x, y center, z half width, y half height. Closed rounded loft."""
    pts=[]; tris=[]
    for x,y,w,h in sections:
        for j in range(steps):
            a=j*2*math.pi/steps
            c=math.copysign(abs(math.cos(a))**exponent,math.cos(a))
            s=math.copysign(abs(math.sin(a))**exponent,math.sin(a))
            pts.append((x,y+h*s,w*c))
    for i in range(len(sections)-1):
        for j in range(steps):
            a=i*steps+j;b=i*steps+(j+1)%steps;c=(i+1)*steps+j;d=(i+1)*steps+(j+1)%steps
            tris.extend(((a,c,b),(b,c,d)))
    # caps: start faces -X, end faces +X
    for k in (0,len(sections)-1):
        idx=len(pts); x,y,_,_=sections[k];pts.append((x,y,0))
        for j in range(steps):
            a=k*steps+j;b=k*steps+(j+1)%steps
            tris.append((idx,a,b) if k==0 else (idx,b,a))
    return make(name,pts,tris,color,roughness,metallic,explode,accent)

def tube(name,path,r,color,roughness=.5,metallic=0.,explode=(0.,0.,0.),accent=False,sides=10):
    pts=[]; tris=[]
    for i,p in enumerate(path):
        tangent=norm(sub(path[min(i+1,len(path)-1)],path[max(i-1,0)]))
        up=(0.,1.,0.) if abs(tangent[1])<.9 else (0.,0.,1.)
        u=norm(cross(tangent,up));v=norm(cross(tangent,u))
        for j in range(sides):
            a=j*2*math.pi/sides
            pts.append(tuple(p[k]+r*(math.cos(a)*u[k]+math.sin(a)*v[k]) for k in range(3)))
    for i in range(len(path)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;c=a+sides;d=b+sides
            tris.extend(((a,b,c),(b,d,c)))
    return make(name,pts,tris,color,roughness,metallic,explode,accent)

def ellipsoid(name,center,scale,color,roughness=.5,metallic=0.,explode=(0.,0.,0.),accent=False):
    sections=[]
    for i in range(19):
        a=-math.pi/2+i*math.pi/18
        sections.append((center[0]+scale[0]*math.sin(a),center[1],max(.0001,scale[2]*math.cos(a)),max(.0001,scale[1]*math.cos(a))))
    return loft(name,sections,color,roughness,metallic,explode,accent,steps=32)

def build():
    parts=[];chalk=[.87,.89,.85];fabric=[.74,.80,.76];dark=[.035,.065,.062];teal=[.19,.49,.44]
    # Dimensions are design units; object is a stylized concept, not manufacturing geometry.
    outline=[(-1.57,.06,.23,.045),(-1.46,.02,.40,.05),(-1.2,0,.49,.052),(-.7,-.012,.49,.052),(-.1,-.005,.43,.052),(.55,.012,.53,.052),(1.14,.07,.57,.05),(1.48,.15,.42,.045),(1.65,.23,.12,.03)]
    parts.append(loft('Outsole',outline,dark,.86,explode=(0,-.65,0),exponent=.45))
    mid=[(x,y+.17,w*.995,.15 if x<1.4 else .10) for x,y,w,h in outline]
    parts.append(loft('Midsole',mid,chalk,.64,explode=(0,-.28,0),exponent=.58))
    upper=[(-1.47,.61,.22,.34),(-1.30,.68,.40,.41),(-1.04,.69,.445,.43),(-.72,.67,.44,.405),(-.42,.61,.41,.35),(-.08,.53,.42,.28),(.35,.46,.48,.22),(.79,.45,.515,.20),(1.14,.44,.495,.16),(1.44,.43,.36,.10),(1.58,.42,.10,.025)]
    parts.append(loft('Upper',upper,fabric,.92,explode=(0,.25,0),exponent=.85))
    def surface_z(x,y):
        for aa,bb in zip(upper,upper[1:]):
            if aa[0]<=x<=bb[0]:
                t=(x-aa[0])/(bb[0]-aa[0]);cy=aa[1]+t*(bb[1]-aa[1]);w=aa[2]+t*(bb[2]-aa[2]);h=aa[3]+t*(bb[3]-aa[3]);q=min(.99,abs((y-cy)/h));return w*(1-q**(2/.85))**(.85/2)
        return .3
    # Side cage panels follow the upper contour; original abstract diagonal ribs, no brand mark.
    for side in (-1,1):
        for j in range(4):
            x=-.91+j*.285
            points=[(x-.12,.34),(x+.04,.55),(x+.26,.82 if x<-.1 else .70)]
            path=[(px,py,side*(surface_z(px,py)+.045)) for px,py in points]
            parts.append(tube(f'Cage_{side}_{j}',path,.045,teal,.37,.12,(0,.25,0),True,12))
        # stitched rim and forefoot wrap
        edge=[(x,y+.235,side*w*.985) for x,y,w,h in outline[1:-1]]
        parts.append(tube(f'Welt_{side}',edge,.018,chalk,.8,explode=(0,-.28,0)))
        toe=[(px,py,side*(surface_z(px,py)+.025)) for px,py in [(.63,.46),(.95,.47),(1.28,.49),(1.46,.47)]]
        parts.append(tube(f'Toe_trim_{side}',toe,.023,chalk,.72,explode=(0,.25,0)))
    # Dark inner collar and contrasting padded lip establish a visibly wearable opening.
    parts.append(ellipsoid('Collar_inner',(-1.015,1.10,0),(.32,.022,.255),dark,.96,explode=(0,.25,0)))
    ring=[(-1.015+.35*math.cos(i*2*math.pi/48),1.102+.025*math.cos(i*2*math.pi/48),.282*math.sin(i*2*math.pi/48)) for i in range(49)]
    parts.append(tube('Collar_padding',ring,.059,fabric,.93,explode=(0,.25,0),sides=12))
    tongue=[(-.77,.93,.14,.065),(-.65,.98,.19,.07),(-.35,.87,.205,.06),(.01,.735,.19,.05),(.36,.635,.14,.035)]
    parts.append(loft('Tongue',tongue,chalk,.89,explode=(0,.43,0),exponent=.55))
    for i in range(6):
        x=-.60+i*.15; y=.998-i*.054
        path=[(x,y,-.245),(x+.085,y+.034,0),(x+.12,y-.035,.235)]
        parts.append(tube(f'Lace_{i}',path,.026,chalk,.87,explode=(0,.43,0),sides=10))
        if i<5:
            parts.append(tube(f'Lace_cross_{i}',[(x,y,.235),(x+.09,y+.015,0),(x+.17,y-.052,-.235)],.024,chalk,.87,explode=(0,.43,0)))
    # Heel clip around rear, in the same accent family.
    heel=[(-1.28,.43,-.41),(-1.49,.46,-.27),(-1.54,.51,0),(-1.49,.46,.27),(-1.28,.43,.41)]
    parts.append(tube('Heel_clip',heel,.073,teal,.25,.30,(0,.25,0),True,14))
    parts.append(tube('Pull_loop',[(-1.40,.95,-.075),(-1.52,1.15,-.075),(-1.52,1.18,.075),(-1.40,.95,.075)],.032,teal,.70,0,(0,.25,0),True,10))
    # Discrete traction pods emphasize construction when separated.
    for i in range(8):
        x=-1.29+i*.365
        for side in (-1,1):
            w=.31 if i in (0,7) else .37
            parts.append(ellipsoid(f'Tread_{i}_{side}',(x,-.071+max(0,x-.5)*.12,side*w),(.105,.048,.082),dark,.90,explode=(0,-.65,0)))
    return dict(generator='original procedural trainer v1',units='design units',up='+Y',forward='+X',parts=parts)

def glb_bytes(model):
    data=bytearray();views=[];accessors=[];meshes=[];materials=[];nodes=[]
    def add(values,kind,component,target):
        while len(data)%4: data.append(0)
        offset=len(data);code='f' if component==5126 else 'I'
        data.extend(struct.pack('<'+str(len(values))+code,*values))
        vi=len(views);views.append(dict(buffer=0,byteOffset=offset,byteLength=len(data)-offset,target=target))
        width=3 if kind=='VEC3' else 1
        a=dict(bufferView=vi,componentType=component,count=len(values)//width,type=kind)
        if kind=='VEC3' and target==34962:
            a['min']=[min(values[j::3]) for j in range(3)];a['max']=[max(values[j::3]) for j in range(3)]
        ai=len(accessors);accessors.append(a);return ai
    for p in model['parts']:
        pos=add(p['positions'],'VEC3',5126,34962);nor=add(p['normals'],'VEC3',5126,34962);ind=add(p['indices'],'SCALAR',5125,34963)
        m=len(materials);materials.append(dict(name=p['name']+'_material',pbrMetallicRoughness=dict(baseColorFactor=p['color']+[1],roughnessFactor=p['roughness'],metallicFactor=p['metallic']),doubleSided=True))
        meshes.append(dict(name=p['name'],primitives=[dict(attributes=dict(POSITION=pos,NORMAL=nor),indices=ind,material=m)]))
        nodes.append(dict(name=p['name'],mesh=len(meshes)-1,extras=dict(explode=p['explode'],accent=p['accent'])))
    doc=dict(asset=dict(version='2.0',generator=model['generator']),scene=0,scenes=[dict(nodes=list(range(len(nodes))))],nodes=nodes,meshes=meshes,materials=materials,accessors=accessors,bufferViews=views,buffers=[dict(byteLength=len(data))],extras=dict(units=model['units'],notice='Original unbranded concept. Not a product scan.'))
    js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4);data+=b'\0'*((-len(data))%4)
    total=12+8+len(js)+8+len(data)
    return struct.pack('<4sII',b'glTF',2,total)+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(data),b'BIN\0')+data

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=ROOT/'assets');ap.add_argument('--overwrite',action='store_true');args=ap.parse_args()
    paths=[args.out/'concept-trainer.json',args.out/'concept-trainer.glb',args.out/'asset-manifest.json',ROOT/'demo'/'mesh-data.js']
    if not args.overwrite and any(p.exists() for p in paths): ap.error('Output exists. Use --overwrite only for owned generated outputs.')
    model=build();args.out.mkdir(parents=True,exist_ok=True);(ROOT/'demo').mkdir(exist_ok=True)
    raw=json.dumps(model,separators=(',',':'))
    paths[0].write_text(raw,encoding='utf-8'); paths[1].write_bytes(glb_bytes(model));paths[3].write_text('window.PRODUCT_MESH='+raw+';\n',encoding='utf-8')
    manifest=dict(schema_version=1,asset_id='concept-trainer-v1',source='scripts/build_asset.py',editable_source='assets/concept-trainer.json',native_blend_status='NOT_BUILT: run blender/build_product.py on a Blender worker',rights=dict(creator='Original asset authored for this kit',license='MIT',third_party_inputs=[]),coordinate_system=dict(up='+Y',forward='+X',units='design units'),parts=[p['name'] for p in model['parts']],triangle_count=sum(len(p['indices'])//3 for p in model['parts']),vertex_count=sum(len(p['positions'])//3 for p in model['parts']),exports=[dict(path='assets/'+p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths[:2]],limitations=['No UVs or texture maps in the canonical seed; add UVs and bake in Blender for production.','Geometry includes overlapping constructive surfaces, not watertight manufacturing topology.','Named parts and explode vectors are semantic test fixtures.'])
    paths[2].write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({k:manifest[k] for k in ('triangle_count','vertex_count')},indent=2))
if __name__=='__main__':main()
