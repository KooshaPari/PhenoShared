#!/usr/bin/env python3
# complexity_analyzer.py - Space/Time complexity analyzer

import os
import sys
import ast
import re
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Set

@dataclass
class Function:
    name: str
    line: int
    complexity: int = 1
    cyclomatic: int = 1
    params: int = 0
    recurses: bool = False
    loops: int = 0
    conditionals: int = 0
    
class ComplexityAnalyzer:
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.functions: List[Function] = []
        self.file_complexities: Dict[str, int] = {}
        self.total_lines = 0
        self.total_functions = 0
        
    def analyze(self):
        """Analyze all Python files"""
        for py_file in self.root.rglob("*.py"):
            if "venv" in str(py_file) or ".venv" in str(py_file):
                continue
            self.analyze_file(py_file)
        return self
    
    def analyze_file(self, filepath: Path):
        """Analyze single file"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            lines = len(content.split('\n'))
            self.total_lines += lines
            
            # Parse AST
            try:
                tree = ast.parse(content)
            except:
                return
                
            funcs = self.extract_functions(tree, filepath.name)
            self.functions.extend(funcs)
            self.total_functions += len(funcs)
            
            # File complexity
            file_complexity = sum(f.complexity for f in funcs)
            self.file_complexities[str(filepath)] = file_complexity
            
        except Exception as e:
            pass
    
    def extract_functions(self, tree: ast.AST, filename: str) -> List[Function]:
        """Extract function complexity metrics"""
        funcs = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func = Function(
                    name=node.name,
                    line=node.lineno,
                    params=len(node.args.args)
                )
                
                # Count complexity contributors
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                        func.conditionals += 1
                        func.complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        func.complexity += len(child.values) - 1
                    elif isinstance(child, (ast.While, ast.For)):
                        func.loops += 1
                    elif isinstance(child, ast.Call):
                        # Check for recursion
                        if hasattr(child.func, 'attr') and child.func.attr == node.name:
                            func.recurses = True
                        elif isinstance(child.func, ast.Name) and child.func.id == node.name:
                            func.recurses = True
                
                funcs.append(func)
        
        return funcs
    
    def worst_functions(self, n: int = 20) -> List[Function]:
        """Get top N most complex functions"""
        return sorted(self.functions, key=lambda f: f.complexity, reverse=True)[:n]
    
    def report(self) -> str:
        """Generate report"""
        lines = []
        lines.append("╔═══════════════════════════════════════════════════════════════╗")
        lines.append("║           COMPLEXITY ANALYSIS REPORT                    ║")
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        lines.append("")
        lines.append(f"Total Files: {len(self.file_complexities)}")
        lines.append(f"Total Functions: {self.total_functions}")
        lines.append(f"Total Lines: {self.total_lines}")
        lines.append(f"Average Complexity: {sum(f.complexity for f in self.functions) / max(1, len(self.functions)):.2f}")
        lines.append("")
        
        lines.append("─── Most Complex Functions ───")
        for func in self.worst_functions(15):
            recursion = " 🔴" if func.recurses else ""
            loops = f" 🔵 x{func.loops}" if func.loops else ""
            lines.append(f"  {func.complexity:3d} | {func.name} (line {func.line}){recursion}{loops}")
        
        lines.append("")
        lines.append("─── Complex Files ───")
        for fpath, comp in sorted(self.file_complexities.items(), key=lambda x: x[1], reverse=True)[:10]:
            fname = Path(fpath).name
            lines.append(f"  {comp:4d} | {fname}")
        
        lines.append("")
        lines.append("─── Complexity Distribution ───")
        ranges = [(1, 5), (6, 10), (11, 20), (21, 50), (51, 100)]
        for low, high in ranges:
            count = len([f for f in self.functions if low <= f.complexity <= high])
            bar = "█" * count + "░" * (50 - count)
            lines.append(f"  {low:3d}-{high:3d}: {bar} {count}")
        
        return "\n".join(lines)

# Rust complexity (simple line-based)
class RustComplexity:
    @staticmethod
    def analyze_rust(root_dir: str) -> dict:
        """Basic Rust complexity analysis"""
        results = {
            'files': 0,
            'functions': 0,
            'lines': 0,
            'impl_blocks': 0,
            'traits': 0,
            'structs': 0,
        }
        
        root = Path(root_dir)
        for rust_file in root.rglob("*.rs"):
            if "target" in str(rust_file):
                continue
            results['files'] += 1
            
            with open(rust_file) as f:
                content = f.read()
                results['lines'] += len(content.split('\n'))
                results['functions'] += len(re.findall(r'fn \w+', content))
                results['impl_blocks'] += len(re.findall(r'impl\s+\w+', content))
                results['traits'] += len(re.findall(r'trait\s+\w+', content))
                results['structs'] += len(re.findall(r'struct\s+\w+', content))
        
        return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Complexity analyzer")
    parser.add_argument("directory", help="Directory to analyze")
    parser.add_argument("--language", choices=["python", "rust"], default="python")
    args = parser.parse_args()
    
    if args.language == "python":
        analyzer = ComplexityAnalyzer(args.directory)
        analyzer.analyze()
        print(analyzer.report())
    else:
        results = RustComplexity.analyze_rust(args.directory)
        print(f"Rust Analysis:")
        print(f"  Files: {results['files']}")
        print(f"  Functions: {results['functions']}")
        print(f"  Lines: {results['lines']}")
        print(f"  Impl blocks: {results['impl_blocks']}")
        print(f"  Traits: {results['traits']}")
        print(f"  Structs: {results['structs']}")
