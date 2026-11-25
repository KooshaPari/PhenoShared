#!/usr/bin/env python3
"""Dependency-only PERT calculator. Refuses to fabricate missing estimates."""
from __future__ import annotations
import argparse, json, sys
from graphlib import TopologicalSorter, CycleError
from pathlib import Path

def estimate(tasks):
    by_id = {t['id']:t for t in tasks}
    if len(by_id)!=len(tasks):raise ValueError('Duplicate work IDs')
    graph={t['id']:set(t['depends_on']) for t in tasks}
    unknown={d for deps in graph.values() for d in deps}-set(graph)
    if unknown:raise ValueError('Unknown dependencies: '+str(sorted(unknown)))
    order=list(TopologicalSorter(graph).static_order())
    missing=[];duration={}
    for t in tasks:
        v=[t['estimate_hours'].get(k) for k in ('optimistic','most_likely','pessimistic')]
        if any(x is None for x in v):missing.append(t['id']);continue
        if any(type(x) not in (int,float) or x<0 for x in v) or not v[0]<=v[1]<=v[2]:
            raise ValueError('Invalid ordered effort estimates: '+t['id'])
        duration[t['id']]=(v[0]+4*v[1]+v[2])/6
    if missing:return {'status':'UNESTIMATED','missing_estimate_ids':missing,'topological_order':order,'critical_path_hours':None,'calendar_forecast':None,'resource_constrained_schedule':False}
    start={};finish={};pred={}
    for i in order:
        best=max(graph[i],key=lambda p:finish[p]) if graph[i] else None
        start[i]=finish[best] if best else 0;finish[i]=start[i]+duration[i];pred[i]=best
    end=max(order,key=lambda i:finish[i]) if order else None
    total=finish[end] if end else 0
    successors={i:[] for i in order}
    for i,ds in graph.items():
        for d in ds:successors[d].append(i)
    latest_start={};latest_finish={}
    for i in reversed(order):
        latest_finish[i]=min(latest_start[s] for s in successors[i]) if successors[i] else total
        latest_start[i]=latest_finish[i]-duration[i]
    path=[];cur=end
    while cur is not None:path.append(cur);cur=pred[cur]
    return {'status':'DEPENDENCY_ONLY_ESTIMATE','critical_path_hours':total,'critical_path':list(reversed(path)),
            'calendar_forecast':None,'resource_constrained_schedule':False,'method':'(O+4M+P)/6; not a probabilistic guarantee',
            'tasks':{i:{'expected_hours':duration[i],'early_start':start[i],'early_finish':finish[i],'slack_hours':latest_start[i]-start[i]} for i in order}}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('tasks',type=Path);a=p.parse_args()
    try:r=estimate(json.loads(a.tasks.read_text()));print(json.dumps(r,indent=2));return 0
    except (OSError,ValueError,KeyError,CycleError) as e:print(json.dumps({'status':'ERROR','error':str(e)}));return 1
if __name__=='__main__':sys.exit(main())
