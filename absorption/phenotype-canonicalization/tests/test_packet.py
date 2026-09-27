from __future__ import annotations
import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import validate_packet as vp

class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in ['decisions.json','pattern-matrix.json','profiles.json','decision-trees.json','audit','migration','examples','schemas']:
            source = ROOT / relative
            destination = self.root / relative
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copyfile(source, destination)
    def tearDown(self):
        self.temp.cleanup()
    def edit(self, name, fn):
        path = self.root / name
        data = json.loads(path.read_text())
        fn(data)
        path.write_text(json.dumps(data))
    def test_valid_packet(self):
        self.assertEqual(vp.validate(self.root), [])
    def test_valid_packet_schemas(self):
        self.assertEqual(vp.validate(self.root, True), [])
    def test_missing_and_empty_dataset(self):
        self.edit('decisions.json', lambda rows: rows.clear())
        self.assertTrue(vp.validate(self.root))
        (self.root/'decisions.json').unlink()
        self.assertTrue(vp.validate(self.root))
    def test_duplicate_and_unknown_evidence(self):
        def change(rows):
            rows.append(copy.deepcopy(rows[0]))
            rows[0]['evidence'].append('NO-SOURCE')
        self.edit('decisions.json', change)
        errors = vp.validate(self.root)
        self.assertTrue(any('duplicate IDs' in e for e in errors))
        self.assertTrue(any('unknown evidence' in e for e in errors))
    def test_unknown_decision_references(self):
        self.edit('profiles.json', lambda rows: rows[0]['decision_ids'].append('NO-DECISION'))
        self.edit('pattern-matrix.json', lambda rows: rows[0].update(decision_id='NO-DECISION'))
        self.assertEqual(sum('unknown decision' in e for e in vp.validate(self.root)), 2)
    def test_unknown_work_and_findings(self):
        def change(rows):
            rows[0]['finding_ids'].append('NO-FINDING')
            rows[0]['hard_dependencies'].append('NO-WORK')
        self.edit('migration/work-packages.json', change)
        self.assertEqual(len(vp.validate(self.root)), 2)
    def test_work_cycle(self):
        self.edit('migration/work-packages.json', lambda rows: rows[0]['hard_dependencies'].append(rows[0]['id']))
        self.assertTrue(any('cycle' in e for e in vp.validate(self.root)))
    def test_tree_start_branch_and_duplicate(self):
        def change(data):
            tree = data['trees'][0]
            tree['start'] = 'NO-START'
            tree['nodes'][0]['when_true'] = 'NO-BRANCH'
            tree['nodes'].append(copy.deepcopy(tree['nodes'][0]))
        self.edit('decision-trees.json', change)
        errors = vp.validate(self.root)
        for text in ('invalid start','unknown branch','duplicate node'):
            self.assertTrue(any(text in e for e in errors))
    def test_tree_cycle(self):
        def change(data):
            node = data['trees'][0]['nodes'][0]
            node['when_true'] = node['id']
        self.edit('decision-trees.json', change)
        self.assertTrue(any('cycle' in e for e in vp.validate(self.root)))
    def test_invalid_example_and_invalid_schema(self):
        self.edit('examples/component.json', lambda row: row.clear())
        self.assertTrue(vp.validate(self.root, True))
        self.edit('schemas/component.schema.json', lambda row: row.update(type=42))
        self.assertTrue(any('invalid schema' in e for e in vp.validate(self.root, True)))
    def test_missing_schema_dependency_fails_explicitly(self):
        with patch.dict(sys.modules, {'jsonschema': None}):
            self.assertTrue(any('NOT run' in e for e in vp.validate(self.root, True)))
    def test_cli_returns_structural_status_only(self):
        with patch.object(sys, 'argv', ['validate_packet.py', str(self.root)]), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(vp.main(), 0)
            self.assertIn('NOT_EVALUATED', output.getvalue())
        self.edit('decisions.json', lambda rows: rows.clear())
        with patch.object(sys, 'argv', ['validate_packet.py', str(self.root)]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vp.main(), 2)

if __name__ == '__main__':
    unittest.main()
