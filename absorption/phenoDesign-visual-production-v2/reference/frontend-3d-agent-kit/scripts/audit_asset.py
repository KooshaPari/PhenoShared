#!/usr/bin/env python3
"""Narrow consistency audit for this kit's uncompressed, internal-buffer GLB.
Not a Khronos validator, trust-signature verifier, or artistic acceptance test.
"""
from __future__ import annotations
import argparse, hashlib, json, math, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def require(condition,message):
    if not condition:raise ValueError(message)
def parse_glb(raw:bytes):
    require(len(raw)>=20,'GLB too short');magic,version,total=struct.unpack_from('<4sII',raw)
    require(magic==b'glTF' and version==2,'Wrong GLB magic/version');require(total==len(raw),'GLB declared length mismatch')
    chunks=[];offset=12
    while offset<len(raw):
        require(offset+8<=len(raw),'Truncated chunk header');length,kind=struct.unpack_from('<I4s',raw,offset);offset+=8
        require(length%4==0 and offset+length<=len(raw),'Invalid chunk boundary/alignment');chunks.append((kind,raw[offset:offset+length]));offset+=length
    require(len(chunks)==2 and chunks[0][0]==b'JSON' and chunks[1][0]==b'BIN\0','Expected one JSON then one BIN chunk')
    doc=json.loads(chunks[0][1]);require(doc.get('asset',{}).get('version')=='2.0','Wrong glTF version');return doc,chunks[1][1]
def audit_glb(raw:bytes):
    doc,binary=parse_glb(raw);require(len(doc['buffers'])==1,'Expected one internal buffer');require('uri' not in doc['buffers'][0],'External buffer unexpected');require(doc['buffers'][0]['byteLength']<=len(binary),'Buffer length exceeds BIN')
    names=[n.get('name') for n in doc['nodes']];require(len(set(names))==len(names),'Duplicate node names');require({'Upper','Midsole','Outsole'}<=set(names),'Missing semantic nodes')
    accessors=doc['accessors'];views=doc['bufferViews']
    def values(index):
        a=accessors[index];v=views[a['bufferView']];require(v.get('buffer')==0,'Wrong buffer');require('byteStride' not in v and 'sparse' not in a,'This checker accepts only simple packed accessors')
        require(a['componentType'] in (5126,5125),'Unsupported component type');require(a['type'] in ('SCALAR','VEC3'),'Unsupported accessor type')
        width=3 if a['type']=='VEC3' else 1;count=a['count'];require(isinstance(count,int) and count>0,'Empty/invalid count');size=count*width*4
        start=v.get('byteOffset',0)+a.get('byteOffset',0);require(start%4==0,'Unaligned accessor');require(a.get('byteOffset',0)+size<=v['byteLength'],'Accessor overflows view');require(start+size<=doc['buffers'][0]['byteLength'],'Accessor exceeds declared buffer')
        code='f' if a['componentType']==5126 else 'I';out=struct.unpack_from('<'+str(count*width)+code,binary,start);require(all(math.isfinite(x) for x in out),'Nonfinite accessor');return out
    triangles=0;vertices=0
    for node in doc['nodes']:
        for prim in doc['meshes'][node['mesh']]['primitives']:
            positions=values(prim['attributes']['POSITION']);normals=values(prim['attributes']['NORMAL']);indices=values(prim['indices']);n=len(positions)//3
            require(len(normals)==len(positions),'Normal count mismatch');require(len(indices)%3==0,'Indices not triangle triples');require(all(0<=i<n for i in indices),'Index out of bounds')
            require(all(.98<math.sqrt(sum(v*v for v in normals[i:i+3]))<1.02 for i in range(0,len(normals),3)),'Non-unit normal')
            triangles+=len(indices)//3;vertices+=n
    return dict(status='PASS',scope='KIT_INTERNAL_GLB_CONSISTENCY_NOT_KHRONOS',bytes=len(raw),nodes=len(names),triangles=triangles,vertices=vertices)
def audit_manifest(root:Path):
    m=json.loads((root/'assets/asset-manifest.json').read_text(encoding='utf-8'));base=root.resolve()
    for entry in m['exports']:
        p=(root/entry['path']).resolve();require(p.is_relative_to(base),'Manifest path escapes kit');require(p.is_file(),'Missing export');raw=p.read_bytes();require(len(raw)==entry['bytes'],'Export byte count mismatch');require(hashlib.sha256(raw).hexdigest()==entry['sha256'],'Export SHA mismatch')
    return m

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=ROOT);a=ap.parse_args();m=audit_manifest(a.root);result=audit_glb((a.root/'assets/concept-trainer.glb').read_bytes());require(result['triangles']==m['triangle_count'],'Triangle manifest mismatch');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
