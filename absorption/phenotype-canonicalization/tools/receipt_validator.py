#!/usr/bin/env python3
"""Synthetic receipt structural/floor checks; NOT producer authentication.

Never use this alone to authorize production promotion. Its input metrics are claims.
Independent trusted instrumentation must supply and authenticate those measurements.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

# Mirrors the Sep 16 handbook's independent floors for this illustrative profile.
FLOORS={'unit_structural':0.85,'unit_behavioral':0.85,'integration':0.85,
        'e2e':0.85,'mutation':0.85,'critical':1.0}


def validate(receipt: dict[str,Any], expected_source: str, expected_evaluator: str) -> list[str]:
    errors=[]
    if not isinstance(receipt,dict):
        return ['receipt must be an object']
    for field,expected in [('source_commit',expected_source),('evaluator_commit',expected_evaluator)]:
        if receipt.get(field) != expected:
            errors.append(f'{field}: missing or wrong revision')
    for field in ('profile_id','tool_fingerprint','producer_id','artifact_digest'):
        if not isinstance(receipt.get(field),str) or not receipt[field].strip():
            errors.append(f'{field}: missing identity')
    rows=receipt.get('measurements')
    if not isinstance(rows,list):
        return errors+['measurements must be a list']
    by_family={}
    for row in rows:
        if not isinstance(row,dict):
            errors.append('measurement must be an object');continue
        family=row.get('family')
        if not isinstance(family,str) or family not in FLOORS:
            errors.append('unknown family');continue
        if family in by_family:
            errors.append(f'{family}: duplicate family')
        by_family[family]=row
    for family,floor in FLOORS.items():
        row=by_family.get(family)
        if row is None:
            errors.append(f'{family}: missing measurement');continue
        if row.get('status') != 'executed':
            errors.append(f'{family}: not executed')
        covered,eligible=row.get('covered'),row.get('eligible')
        numeric=all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in (covered,eligible))
        if not numeric or eligible <= 0 or covered < 0 or covered > eligible:
            errors.append(f'{family}: invalid/empty denominator or numerator');continue
        if covered / eligible < floor:
            errors.append(f'{family}: below independent floor')
        if any(type(row.get(field)) is not int or row[field] != 0 for field in ('failed', 'exit_code')):
            errors.append(f'{family}: failed behavior or unsuccessful instrument')
        if not isinstance(row.get('evidence_ref'),str) or not row['evidence_ref'].strip():
            errors.append(f'{family}: missing evidence reference')
    return errors


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt',type=Path)
    parser.add_argument('--expected-source',required=True)
    parser.add_argument('--expected-evaluator',required=True)
    args=parser.parse_args()
    try:
        receipt=json.loads(args.receipt.read_text())
        errors=validate(receipt,args.expected_source,args.expected_evaluator)
    except (OSError,ValueError) as exc:
        print(json.dumps({'status':'INVALID','errors':[str(exc)]}));return 2
    print(json.dumps({'status':'INVALID' if errors else 'STRUCTURALLY_VALID_NOT_AUTHENTICATED',
        'production_qualification':'NOT_EVALUATED','errors':errors},indent=2))
    return 2 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
