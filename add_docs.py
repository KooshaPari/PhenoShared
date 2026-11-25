#!/usr/bin/env python3
"""Add doc comments to enum variants and other public items in Rust files."""

import re
import sys

def add_docs_to_file(text):
    lines = text.split('\n')
    result = []
    brace_depth = 0
    in_enum = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Detect enum start
        if re.match(r'^(pub\s+)?enum\s+', stripped):
            in_enum = True
            # Count braces on this line to set initial depth
            brace_depth = stripped.count('{') - stripped.count('}')
        
        # Track braces for enum depth
        if in_enum:
            if not re.match(r'^(pub\s+)?enum\s+', stripped):
                brace_depth += stripped.count('{') - stripped.count('}')
            if brace_depth <= 0:
                in_enum = False
        
        # Check if this line is an enum variant (inside enum, indented, starts with capital letter)
        if in_enum and stripped and not stripped.startswith('//') and not stripped.startswith('#['):
            if re.match(r'^[A-Z][A-Za-z0-9_]*,?$', stripped) or re.match(r'^[A-Z][A-Za-z0-9_]*\([^)]*\),?$', stripped):
                # Check if previous non-empty line is a doc comment
                has_doc = False
                for j in range(len(result) - 1, -1, -1):
                    prev = result[j].strip()
                    if prev == '':
                        continue
                    if prev.startswith('///') or prev.startswith('//') or prev.startswith('#['):
                        has_doc = True
                    break
                if not has_doc:
                    variant_name = stripped.split('(')[0].rstrip(',')
                    indent = line[:len(line) - len(line.lstrip())]
                    result.append(f'{indent}/// `{variant_name}`')
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: add_docs.py <file>")
        sys.exit(1)
    
    with open(sys.argv[1], 'r') as f:
        content = f.read()
    
    new_content = add_docs_to_file(content)
    
    with open(sys.argv[1], 'w') as f:
        f.write(new_content)
    
    print(f"Updated {sys.argv[1]}")
