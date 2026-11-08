import ast
import os
import re
from typing import List, Dict, Any, Set, Tuple
from rich.console import Console
from dataclasses import dataclass
from enum import Enum

console = Console()

class Severity(str, Enum):
    """Risk severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class FindingPattern:
    """Pattern detection result with context."""
    pattern: str
    severity: Severity
    category: str
    evidence: List[str]

class TriageEngine:
    """Enhanced static and heuristic triage engine for malicious dependency detection."""

    # Core suspicious operations
    DANGEROUS_FUNCTIONS = {
        "eval": "dynamic_code_execution",
        "exec": "dynamic_code_execution",
        "__import__": "dynamic_import",
        "compile": "dynamic_compilation",
        "globals": "global_state_access",
        "locals": "local_state_access",
        "vars": "object_introspection"
    }

    # Network operations (indicative of exfiltration)
    NETWORK_OPERATIONS = {
        "requests.post": "http_post",
        "requests.get": "http_request",
        "urllib.request.urlopen": "url_open",
        "urllib.request.urlretrieve": "file_download",
        "socket.socket": "socket_creation",
        "socket.connect": "socket_connect",
        "http.client.HTTPConnection": "http_client",
        "ftplib.FTP": "ftp_client"
    }

    # Encoding/obfuscation (suspicious when combined with network ops)
    ENCODING_OPERATIONS = {
        "base64.b64decode": "base64_decode",
        "base64.b64encode": "base64_encode",
        "binascii.unhexlify": "hex_decode",
        "codecs.decode": "codec_decode",
        "base64.a85decode": "ascii85_decode"
    }

    # File/shell operations (escalation risk)
    SYSTEM_OPERATIONS = {
        "subprocess.Popen": "process_execution",
        "subprocess.run": "process_run",
        "subprocess.call": "process_call",
        "os.system": "shell_command",
        "os.popen": "pipe_open",
        "shutil.rmtree": "recursive_delete",
        "os.remove": "file_delete",
        "open": "file_operations"
    }

    def __init__(self):
        self.findings: List[Dict[str, Any]] = []

    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Scan a single file for suspicious patterns using AST and heuristics."""
        findings = []
        if not os.path.exists(file_path):
            return findings

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Extract findings with risk assessment
            findings = self._analyze_content(content, file_path)

        except SyntaxError:
            # File may not be valid Python (e.g., .pth file)
            findings = self._heuristic_scan(content, file_path)
        except Exception as e:
            console.print(f"[red]Error scanning {file_path}:[/red] {e}")

        return findings

    def _analyze_content(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Full analysis including AST and heuristics."""
        findings = []

        # 1. Heuristic pattern matching
        findings.extend(self._heuristic_scan(content, file_path))

        # 2. AST Analysis (if valid Python)
        try:
            tree = ast.parse(content)
            findings.extend(self._ast_analysis(tree, content, file_path))
        except SyntaxError:
            pass

        # 3. Deduplication and risk assessment
        findings = self._deduplicate_findings(findings)
        findings = self._assess_risk(findings, content)

        return findings

    def _heuristic_scan(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Scan using keyword and regex heuristics."""
        findings = []

        # Dangerous function calls
        for func, category in self.DANGEROUS_FUNCTIONS.items():
            pattern = rf"\b{re.escape(func)}\s*\("
            if re.search(pattern, content):
                findings.append({
                    "type": "heuristic",
                    "pattern": func,
                    "category": category,
                    "file": file_path,
                    "severity": "high"
                })

        # Network operations
        for op, category in self.NETWORK_OPERATIONS.items():
            if op in content:
                findings.append({
                    "type": "heuristic",
                    "pattern": op,
                    "category": category,
                    "file": file_path,
                    "severity": "medium"
                })

        # Encoding operations
        for op, category in self.ENCODING_OPERATIONS.items():
            if op in content:
                findings.append({
                    "type": "heuristic",
                    "pattern": op,
                    "category": category,
                    "file": file_path,
                    "severity": "low"
                })

        # System operations
        for op, category in self.SYSTEM_OPERATIONS.items():
            pattern = rf"\b{re.escape(op.split('.')[-1])}\s*\("
            if re.search(pattern, content):
                findings.append({
                    "type": "heuristic",
                    "pattern": op,
                    "category": category,
                    "file": file_path,
                    "severity": "high"
                })

        # Obfuscation markers
        obfuscation_patterns = [
            (r"__\w+__\s*=", "dunder_assignment"),
            (r"[\x00-\x08\x0e-\x1f]", "non_printable_chars"),
            (r"\\x[0-9a-f]{2}", "hex_escapes"),
            (r"rot13|ROT13", "rot13_encoding"),
            (r"marshal\.", "marshal_usage"),
            (r"pickle\.", "pickle_usage"),
        ]

        for pattern, category in obfuscation_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                findings.append({
                    "type": "obfuscation",
                    "pattern": category,
                    "category": category,
                    "file": file_path,
                    "severity": "medium"
                })

        return findings

    def _ast_analysis(self, tree: ast.AST, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Deep AST-based analysis for Python files."""
        findings = []

        for node in ast.walk(tree):
            # Detect dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.DANGEROUS_FUNCTIONS:
                        findings.append({
                            "type": "ast",
                            "pattern": f"call_{node.func.id}",
                            "category": self.DANGEROUS_FUNCTIONS[node.func.id],
                            "file": file_path,
                            "severity": "high",
                            "lineno": node.lineno
                        })

                # Detect method calls on dangerous modules
                elif isinstance(node.func, ast.Attribute):
                    full_call = ast.unparse(node.func) if hasattr(ast, 'unparse') else ""
                    if any(op in full_call for op in self.NETWORK_OPERATIONS):
                        findings.append({
                            "type": "ast",
                            "pattern": full_call,
                            "category": "network_operation",
                            "file": file_path,
                            "severity": "medium",
                            "lineno": node.lineno
                        })

        # Detect environment variable access (credential exfiltration)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "environ":
                        findings.append({
                            "type": "ast",
                            "pattern": "os.environ_access",
                            "category": "credential_access",
                            "file": file_path,
                            "severity": "high",
                            "lineno": node.lineno
                        })

        return findings

    def _deduplicate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate findings."""
        seen: Set[Tuple[str, str, str]] = set()
        unique = []

        for finding in findings:
            key = (finding.get("pattern"), finding.get("file"), finding.get("severity"))
            if key not in seen:
                seen.add(key)
                unique.append(finding)

        return unique

    def _assess_risk(self, findings: List[Dict[str, Any]], content: str) -> List[Dict[str, Any]]:
        """Assess combined risk based on multiple findings."""
        enhanced = []

        # Count dangerous pattern combinations
        has_encoding = any("encode" in f.get("category", "").lower() or "decode" in f.get("category", "").lower() for f in findings)
        has_network = any("network" in f.get("category", "") or "http" in f.get("category", "") or "socket" in f.get("category", "") for f in findings)
        has_dynamic = any("dynamic" in f.get("category", "") for f in findings)

        for finding in findings:
            # Upgrade severity if multiple dangerous patterns detected
            if has_encoding and has_network and finding.get("severity") != "high":
                finding["severity"] = "high"
                finding["reason"] = "encoding_network_combo"

            if has_dynamic and has_network:
                finding["severity"] = "critical"
                finding["reason"] = "dynamic_code_network_combo"

            enhanced.append(finding)

        return enhanced

    def triage_dependency(self, dep_path: str) -> List[Dict[str, Any]]:
        """Triage an entire dependency directory."""
        all_findings = []
        # Target sensitive files like .pth, setup.py, and core logic
        target_extensions = [".py", ".pth", ".sh", ".js"]
        target_filenames = ["setup.py", "install.py", "preinstall.js", "postinstall.js", "__init__.py"]

        for root, _, files in os.walk(dep_path):
            for file in files:
                if file.endswith(tuple(target_extensions)) or file in target_filenames:
                    file_path = os.path.join(root, file)
                    all_findings.extend(self.scan_file(file_path))

        return all_findings
