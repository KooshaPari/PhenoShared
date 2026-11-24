"""Generate AGENTS.md from a spec dict.

Usage::

    from pheno_agents_md import generate
    generate({
        "repo": "pheno-config",
        "tier": 0,
        "language": "Rust",
        ...
    }, out_path=Path("AGENTS.md"))
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

REQUIRED_SECTIONS = [
    "purpose",
    "public_api",
    "conventions",
    "quality",
    "see_also",
]

TIERS = {0, 1, 2, 3, 4}


def generate(spec: dict[str, Any], out_path: Path) -> None:
    """Render ``spec`` to ``out_path`` as Markdown.

    Raises ``ValueError`` if the spec fails validation.
    """
    _validate(spec)
    text = _render(spec)
    out_path.write_text(text, encoding="utf-8")


def lint(path: Path) -> list[str]:
    """Return a list of lint errors for the given AGENTS.md file."""
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    for section in REQUIRED_SECTIONS:
        marker = f"## {section.replace('_', ' ').title()}"
        if marker.lower() not in text.lower():
            errors.append(f"missing section: {marker}")
    return errors


def _validate(spec: dict[str, Any]) -> None:
    if "repo" not in spec:
        raise ValueError("spec.repo is required")
    if spec.get("tier") not in TIERS:
        raise ValueError(f"spec.tier must be one of {sorted(TIERS)}")
    for section in REQUIRED_SECTIONS:
        if section not in spec:
            raise ValueError(f"spec.{section} is required")


def _render(spec: dict[str, Any]) -> str:
    repo = spec["repo"]
    tier = spec["tier"]
    language = spec.get("language", "Rust")
    maturity = spec.get("maturity", "alpha")

    lines = [
        f"# {repo}",
        "",
        f"**Tier:** {tier}",
        f"**Language:** {language}",
        f"**Maturity:** {maturity}",
        "",
        "## Purpose",
        "",
        spec["purpose"],
        "",
        "## Public API",
        "",
    ]
    for entry in spec["public_api"]:
        name = entry["name"]
        sig = entry.get("sig", "")
        kind = entry.get("kind", "function")
        if sig:
            lines.append(f"- `{kind} {name}({sig})`")
        else:
            lines.append(f"- `{kind} {name}`")
    lines.append("")

    lines.append("## Conventions")
    lines.append("")
    conv = spec["conventions"]
    lines.append(f"**When to use:** {conv.get('when_to_use', '')}")
    lines.append("")
    lines.append(f"**When NOT to use:** {conv.get('when_not_to_use', '')}")
    lines.append("")
    lines.append("**5-line quickstart:**")
    lines.append("")
    lines.append("```bash")
    for step in conv.get("quickstart", []):
        lines.append(step)
    lines.append("```")
    lines.append("")

    lines.append("## Quality Bar")
    lines.append("")
    q = spec.get("quality", {})
    for key in ("pillars", "tests", "ci", "license", "coverage"):
        if key in q:
            lines.append(f"- **{key}:** {q[key]}")
    lines.append("")

    lines.append("## See also")
    lines.append("")
    for entry in spec.get("see_also", []):
        lines.append(f"- [{entry['title']}]({entry['href']})")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    generate(spec, args.out)