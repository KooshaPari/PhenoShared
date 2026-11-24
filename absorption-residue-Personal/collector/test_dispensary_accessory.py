"""Regression: accessories must not enter the dispensary snapshot (and so never trigger price alerts)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "worker" / "index.js"

CASES = [
    ("Cart / AIO Silicone Cap Dime Industries - One Size", False),
    ("Stiiizy Pod Case", False),
    ("Cart Battery 510", False),
    ("510 Charger", False),
    ("Jetty Extracts Cart 1g", True),
    ("Raw Garden Pod 0.5g", True),
    ("Disposable AIO Vape 1g", True),
    ("Dime Industries Cartridge 1g", True),
]


@unittest.skipUnless(shutil.which("node"), "node not available")
class AccessoryFilterTests(unittest.TestCase):
    def test_keep_drops_accessories_and_keeps_products(self):
        script = (
            "import(%s).then(m=>{const out=%s.map(([n])=>!!m.keep("
            "{id:1,slug:'x',name:n,category:{name:'Vape'},price:{price:6.5}},1.2));"
            "console.log(JSON.stringify(out))})"
        ) % (json.dumps(WORKER.as_uri()), json.dumps(CASES))
        res = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        got = json.loads(res.stdout.strip().splitlines()[-1])
        for (name, want), kept in zip(CASES, got):
            self.assertEqual(kept, want, name)


if __name__ == "__main__":
    unittest.main()
