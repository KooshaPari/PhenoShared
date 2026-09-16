#!/usr/bin/env python3
"""Offline documentation/registry validation. Does not qualify any product."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from collections import Counter
from graphlib import TopologicalSorter, CycleError
from pathlib import Path
import jsonschema


def validate_records(requirements, tasks, trace, products, roster, spec_ids):
    errors=[]
    def unique(items,key,label):
        vals=[x[key] for x in items]
        if len(vals)!=len(set(vals)):errors.append('duplicate '+label)
        return set(vals)
    rids=unique(requirements,'id','requirement');tids=unique(tasks,'id','task');pids=unique(products,'id','product')
    unique(trace,'requirement_id','trace')
    if {x['requirement_id'] for x in trace}!=rids:errors.append('trace requirement population mismatch')
    for r in requirements:
        if r['spec_id'] not in spec_ids:errors.append('unknown spec '+r['id'])
        if not r.get('acceptance') or not r.get('sources'):errors.append('missing acceptance/source '+r['id'])
    for t in tasks:
        if not set(t['depends_on'])<=tids:errors.append('unknown dependency '+t['id'])
        if not set(t['requirements'])<=rids:errors.append('unknown task requirement '+t['id'])
        if t.get('mutation_authorized') is not False:errors.append('unexpected mutation authority '+t['id'])
        if t['status']!='PLANNED_NOT_CLAIMED':errors.append('fabricated task status '+t['id'])
    try:tuple(TopologicalSorter({t['id']:set(t['depends_on']) for t in tasks}).static_order())
    except CycleError:errors.append('task cycle')
    for x in trace:
        if not set(x['work_ids'])<=tids:errors.append('unknown trace work')
        if not x['work_ids']:errors.append('orphan requirement '+x['requirement_id'])
        for tid in x['work_ids']:
            t=next((t for t in tasks if t['id']==tid),None)
            if t and x['requirement_id'] not in t['requirements']:errors.append('inconsistent trace edge')
        if x['actual_product_evidence_ids']:errors.append('fabricated product evidence in proposed program')
    entries=roster['entries'];unique(entries,'id','roster')
    if {x['id'] for x in entries if x['class']=='product-or-lab'}!=pids:errors.append('product roster mismatch')
    capacity=sum(x['planned_seats'] for x in entries)
    if capacity!=roster['product_session_capacity']:errors.append('seat count mismatch')
    if sum(x['class']=='product-or-lab' for x in entries)!=roster['product_labs']:errors.append('product count mismatch')
    return errors


def validate(root: Path):
    errors=[];checks=[];data={}
    def check(name,fn):
        try:fn();checks.append({'name':name,'status':'PASS'})
        except Exception as e:errors.append(name+': '+str(e));checks.append({'name':name,'status':'FAIL'})
    def load(path):
        if path not in data:data[path]=json.loads((root/path).read_text(encoding='utf-8'))
        return data[path]
    check('all JSON parses',lambda:[load(str(p.relative_to(root))) for p in root.rglob('*.json')])
    schemafiles=list((root/'schemas').glob('*.schema.json'))
    check('schemas valid 2020-12',lambda:[jsonschema.Draft202012Validator.check_schema(json.loads(p.read_text())) for p in schemafiles])
    for pair in load('examples/schema-index.json'):
        check('schema example '+pair['path'],lambda pair=pair:jsonschema.Draft202012Validator(load(pair['schema'])).validate(load(pair['path'])))
    check('topic proposals schema',lambda:[jsonschema.Draft202012Validator(load('schemas/topic-proposal.schema.json')).validate(x) for x in load('portfolio/topic-proposals.json')])
    def core():
        metas=[json.loads(p.read_text()) for p in (root/'specs').glob('*/meta.json')]
        r=validate_records(load('records/requirements.json'),load('work/tasks.json'),load('records/traceability.json'),load('records/products.json'),load('portfolio/planning-roster.json'),{m['id'] for m in metas})
        if r:raise ValueError('; '.join(r))
    check('IDs DAG trace and allocation',core)
    def specs():
        for p in (root/'specs').glob('*/meta.json'):
            m=json.loads(p.read_text())
            assert m['state']=='proposed' and m['engine_receipt'] is None and m['human_approval'] is None
            for n in ('spec.md','plan.md','tasks.md','research.md'):assert (p.parent/n).is_file(),str(p.parent/n)
    check('provisional spec bundles',specs)
    def pilots():
        for p in load('records/products.json'):
            assert (root/p['dossier']).is_file()
            pilot=load(p['pilot']);assert pilot['product_id']==p['id']
            assert pilot['results'] is None and pilot['winner'] is None and pilot['status']=='PLANNED_NOT_EXECUTED'
    check('all product plans and no invented pilot results',pilots)
    def links():
        broken=[]
        for p in root.rglob('*.md'):
            for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)',p.read_text(encoding='utf-8')):
                if '://' in target or target.startswith(('#','mailto:','sandbox:')):continue
                target=target.split('#',1)[0]
                if not target:continue
                candidate=(p.parent/target).resolve()
                if not candidate.is_relative_to(root.resolve()) or not candidate.exists():broken.append(str(p.relative_to(root))+' -> '+target)
        if broken:raise ValueError('; '.join(broken))
    check('relative Markdown file targets',links)
    def preserved():
        for x in load('references/input-manifest.json'):
            p=root/x['path'];assert p.stat().st_size==x['size_bytes']
            assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path']
        for x in load('intent/provenance.json')['messages']:
            assert hashlib.sha256((root/'intent'/x['path']).read_bytes()).hexdigest()==x['sha256']
    check('prior archives and prompt integrity',preserved)
    def files():
        for p in root.rglob('*'):
            assert not p.is_symlink(),str(p)
            if p.is_file():assert p.stat().st_size>0,str(p)
        assert not any(root.rglob('*.ttf')) and not any(root.rglob('*.otf'))
    check('no empty files symlinks or font binaries',files)
    return {'status':'PASS' if not errors else 'FAIL','checks':checks,'errors':errors,'product_tests_executed':False,'product_qualification':False,'fresh_github_audit':False,'external_links_checked':False,'anchor_targets_checked':False,'semantic_document_completeness_certified':False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path,nargs='?',default=Path(__file__).resolve().parents[1]);a=p.parse_args(argv)
    try:r=validate(a.root.resolve());print(json.dumps(r,indent=2));return 0 if r['status']=='PASS' else 1
    except Exception as e:print(json.dumps({'status':'INPUT_ERROR','error':str(e),'product_qualification':False}));return 2
if __name__=='__main__':sys.exit(main())
