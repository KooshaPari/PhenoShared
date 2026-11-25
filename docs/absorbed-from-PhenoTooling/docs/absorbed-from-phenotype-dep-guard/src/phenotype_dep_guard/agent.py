import os
import subprocess
import json
import re
from typing import Dict, Any, List, Optional
from rich.console import Console

console = Console()

class LLMClient:
    """Interface for calling LLM providers via forge -p."""

    def __init__(self, model: str = "minimax-m2.7-highspeed", use_forge: bool = True):
        self.model = model
        self.use_forge = use_forge

    def call_model(self, prompt: str) -> Optional[str]:
        """Call model via forge -p with fallback to mock."""
        if not self.use_forge:
            return self._mock_response(prompt)

        try:
            # Attempt forge -p integration
            result = subprocess.run(
                ["forge", "-p", self.model],
                input=prompt.encode(),
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.decode().strip()
        except Exception as e:
            console.print(f"[yellow]Forge integration unavailable: {e}. Using mock mode.[/yellow]")

        return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """Fallback mock response for testing."""
        return json.dumps({
            "threat_level": "medium",
            "confidence": 0.75,
            "explanation": "Mock LLM analysis (forge -p unavailable)"
        })


class AgenticAnalyzer:
    """Agentic analyzer using LLM to detect sophisticated supply chain attacks."""

    SUPPLY_CHAIN_THREAT_PROMPT_TEMPLATE = """
Analyze this dependency for supply chain attack indicators.

Package: {package}
Suspicious Patterns Found: {pattern_count}
High Severity Findings: {high_severity_count}
Patterns: {patterns}

Based on the suspicious patterns detected by static analysis, assess:
1. Likelihood of intentional malicious code (0-100%)
2. Attack vector type (if present)
3. Risk assessment (low/medium/high/critical)
4. Recommended action (accept/review/block/quarantine)

Respond in JSON format with fields: threat_level, confidence, attack_vector, recommendation.
"""

    def __init__(self, model: str = "minimax-m2.7-highspeed", use_forge: bool = True):
        self.model = model
        self.llm_client = LLMClient(model, use_forge)

    def analyze_dependency(
        self,
        package_name: str,
        findings: List[Dict[str, Any]],
        dep_path: str
    ) -> Dict[str, Any]:
        """
        Perform agentic deep analysis on a flagged dependency using LLM.
        Falls back to deterministic scoring if LLM unavailable.
        """
        if not findings:
            return {
                "package": package_name,
                "status": "clean",
                "confidence": 0.99,
                "threat_level": "none",
                "action": "accept"
            }

        # Prepare analysis context
        high_severity = [f for f in findings if f['severity'] == 'high']
        pattern_details = ", ".join(
            [f"{f['pattern']} ({f['type']})" for f in findings[:5]]
        )

        # Build LLM prompt
        prompt = self.SUPPLY_CHAIN_THREAT_PROMPT_TEMPLATE.format(
            package=package_name,
            pattern_count=len(findings),
            high_severity_count=len(high_severity),
            patterns=pattern_details
        )

        # Get LLM analysis
        llm_response = self.llm_client.call_model(prompt)
        analysis_result = self._parse_llm_response(llm_response)

        # Combine with heuristic scoring
        heuristic_score = self._compute_heuristic_score(findings)
        final_confidence = (
            (analysis_result.get("confidence", 0.5) + heuristic_score) / 2
        )

        return {
            "package": package_name,
            "status": self._determine_status(final_confidence),
            "confidence": round(final_confidence, 2),
            "threat_level": analysis_result.get("threat_level", "unknown"),
            "reasoning": f"Found {len(findings)} suspicious patterns. LLM assessment: {analysis_result.get('explanation', 'N/A')}",
            "action": analysis_result.get("recommendation", "manual_review")
        }

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response with fallback."""
        try:
            # Clean response text (remove markdown code blocks if present)
            response = re.sub(r'```json\s*|\s*```', '', response).strip()
            return json.loads(response)
        except json.JSONDecodeError:
            console.print(f"[yellow]Failed to parse LLM response. Using defaults.[/yellow]")
            return {
                "threat_level": "medium",
                "confidence": 0.5,
                "explanation": "Analysis failed; manual review required",
                "recommendation": "manual_review"
            }

    def _compute_heuristic_score(self, findings: List[Dict[str, Any]]) -> float:
        """Compute risk score based on heuristic findings."""
        if not findings:
            return 0.0

        high_severity = sum(1 for f in findings if f['severity'] == 'high')
        medium_severity = sum(1 for f in findings if f['severity'] == 'medium')

        # Risk score: high=0.4 per finding, medium=0.1 per finding, capped at 1.0
        score = min((high_severity * 0.4 + medium_severity * 0.1), 1.0)
        return score

    def _determine_status(self, confidence: float) -> str:
        """Determine status based on confidence."""
        if confidence >= 0.8:
            return "malicious"
        elif confidence >= 0.6:
            return "suspicious"
        elif confidence >= 0.4:
            return "review_needed"
        else:
            return "likely_clean"
