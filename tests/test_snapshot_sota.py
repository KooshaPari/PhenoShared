from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.cron import snapshot_sota


class SnapshotSotaTests(unittest.TestCase):
    def test_snapshot_inventories_same_day_artifacts_except_its_own_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            out_root = Path(temporary) / "sota"
            snapshot_date = snapshot_sota.datetime.datetime.now(
                tz=snapshot_sota.datetime.timezone.utc
            ).strftime("%Y-%m-%d")
            day_dir = out_root / snapshot_date
            nested = day_dir / "helper" / "measurement.json"
            nested.parent.mkdir(parents=True)
            nested.write_bytes(b'{"latency_ms": 42}\n')
            root_artifact = day_dir / "primary.log"
            root_artifact.write_bytes(b"primary inference evidence\n")
            (day_dir / "snapshot.json").write_text("old snapshot\n")
            (day_dir / "snapshot.sha256").write_text("old checksum\n")

            snapshot_path = snapshot_sota.take_snapshot(out_root)
            snapshot = json.loads(snapshot_path.read_text())

        self.assertEqual(
            snapshot["same_day_files"],
            [
                {
                    "path": "helper/measurement.json",
                    "size_bytes": len(b'{"latency_ms": 42}\n'),
                    "sha256": hashlib.sha256(b'{"latency_ms": 42}\n').hexdigest(),
                },
                {
                    "path": "primary.log",
                    "size_bytes": len(b"primary inference evidence\n"),
                    "sha256": hashlib.sha256(
                        b"primary inference evidence\n"
                    ).hexdigest(),
                },
            ],
        )
