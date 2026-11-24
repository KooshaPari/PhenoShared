from phenotype_dep_guard.triage import TriageEngine
import os

def test_triage_malicious_pth():
    triage = TriageEngine()
    sample_path = "/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-dep-guard/tests/samples/malicious_pkg"
    
    findings = triage.triage_dependency(sample_path)
    print(f"Found {len(findings)} findings in {sample_path}")
    for finding in findings:
        print(f"[{finding['severity']}] {finding['type']}: {finding['pattern']} in {finding['file']}")
    
    assert len(findings) > 0
    assert any(f['severity'] == 'high' for f in findings)
    assert any(f['type'] == 'ast' and 'dynamic_exec' in f['pattern'] for f in findings)

if __name__ == "__main__":
    test_triage_malicious_pth()
