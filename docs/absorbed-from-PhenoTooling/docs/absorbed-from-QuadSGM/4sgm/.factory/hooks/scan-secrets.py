#!/usr/bin/env python3
"""
Secret Scanner Hook
Blocks commits with exposed secrets, API keys, or credentials
"""

import json
import re
import sys

# Patterns for common secrets
SECRET_PATTERNS = [
    (r"sk-ant-[a-zA-Z0-9]{40,}", "Anthropic API key"),
    (r"sk-[a-zA-Z0-9]{40,}", "OpenAI API key"),
    (r"eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}", "Supabase JWT token"),
    (r"postgres://[^@]+:[^@]+@[^/]+", "PostgreSQL connection string"),
    (r'ANTHROPIC_API_KEY\s*=\s*["\']?sk-ant-[a-zA-Z0-9]+', "Hardcoded Anthropic key"),
    (r'OPENAI_API_KEY\s*=\s*["\']?sk-[a-zA-Z0-9]+', "Hardcoded OpenAI key"),
    (r'SUPABASE_KEY\s*=\s*["\']?eyJ[a-zA-Z0-9_-]+', "Hardcoded Supabase key"),
    (r'password\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded password"),
    (r"-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----", "Private key"),
]

# Allowed patterns (e.g., in example files)
ALLOWED_FILES = [
    ".env.example",
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    "WARP.md",
    ".md",
]

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

file_path = input_data.get("tool_input", {}).get("file_path", "")
content = input_data.get("tool_input", {}).get("content", "")

# Skip allowed files
if any(allowed in file_path for allowed in ALLOWED_FILES):
    sys.exit(0)

# Scan for secrets
issues = []
for pattern, description in SECRET_PATTERNS:
    matches = re.findall(pattern, content, re.IGNORECASE)
    if matches:
        # Mask the secret for display
        masked = [m[:10] + "..." if len(m) > 10 else m for m in matches]
        issues.append(f"  • {description}: {', '.join(masked)}")

if issues:
    print(f"❌ Security violation in {file_path}:", file=sys.stderr)
    for issue in issues:
        print(issue, file=sys.stderr)
    print(
        "\n⚠️  Remove secrets from code. Use environment variables instead.",
        file=sys.stderr,
    )
    print("    Example: os.getenv('ANTHROPIC_API_KEY')", file=sys.stderr)
    sys.exit(2)  # Block

sys.exit(0)
