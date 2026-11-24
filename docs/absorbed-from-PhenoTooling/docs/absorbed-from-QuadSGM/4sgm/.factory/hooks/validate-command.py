#!/usr/bin/env python3
"""
Command Validation Hook
Validates commands before execution to prevent dangerous operations
"""

import json
import sys
import re

# Dangerous command patterns
DANGEROUS_PATTERNS = [
    (r"rm\s+-rf\s+/", "Recursive delete from root"),
    (r"rm\s+-rf\s+~", "Recursive delete from home"),
    (r"DROP\s+TABLE", "SQL DROP TABLE"),
    (r"DELETE\s+FROM\s+\w+\s*;?\s*$", "SQL DELETE without WHERE"),
    (r"git\s+push\s+--force", "Force push to remote"),
    (r"pip\s+uninstall.*-y", "Uninstall without confirmation"),
]

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)  # Can't parse, allow

command = input_data.get("tool_input", {}).get("command", "")

# Check for dangerous patterns
for pattern, description in DANGEROUS_PATTERNS:
    if re.search(pattern, command, re.IGNORECASE):
        print("⚠️  Potentially dangerous command detected:", file=sys.stderr)
        print(f"   Command: {command}", file=sys.stderr)
        print(f"   Risk: {description}", file=sys.stderr)
        print("", file=sys.stderr)
        print("   If you're sure, run manually.", file=sys.stderr)
        sys.exit(2)  # Block

sys.exit(0)
