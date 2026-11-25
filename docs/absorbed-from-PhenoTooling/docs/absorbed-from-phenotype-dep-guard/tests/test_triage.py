from phenotype_dep_guard.triage import TriageEngine
import os

def test_triage_basic():
    engine = TriageEngine()
    # Create a dummy suspicious file
    with open("suspicious_test.py", "w") as f:
        f.write("import os\nos.system('rm -rf /')\neval('import base64')")
    
    findings = engine.scan_file("suspicious_test.py")
    assert len(findings) >= 2
    os.remove("suspicious_test.py")

def test_triage_benign():
    engine = TriageEngine()
    with open("benign_test.py", "w") as f:
        f.write("def hello():\n    print('Hello world')")
    
    findings = engine.scan_file("benign_test.py")
    assert len(findings) == 0
    os.remove("benign_test.py")
