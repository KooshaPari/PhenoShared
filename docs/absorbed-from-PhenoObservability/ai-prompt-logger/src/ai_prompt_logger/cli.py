"""CLI for AI Prompt Logger."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ai_prompt_logger import logger

app = typer.Typer(help="AI Prompt Logger CLI - Scrape and manage prompts from AI agents")
console = Console()


@app.command()
def log(
    prompt: str = typer.Argument(..., help="The prompt text to log"),
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name (cursor, forge, codex, claude, etc.)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model used"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file (default: prompts.jsonl)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Log a prompt to the database."""
    try:
        entry = logger.log_prompt(
            prompt=prompt,
            agent=agent,
            model=model or "unknown",
        )
        
        if verbose:
            console.print("[green]Logged prompt:[/green]")
            console.print(f"  Agent: {entry.agent}")
            console.print(f"  Model: {entry.model}")
            console.print(f"  ID: {entry.id}")
            console.print(f"  Timestamp: {entry.timestamp}")
        else:
            console.print(f"[green]✓[/green] Logged prompt {entry.id} from {agent}")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def list(
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of entries to show"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full prompts"),
) -> None:
    """List logged prompts."""
    try:
        entries = logger.list_prompts(agent=agent, limit=limit)
        
        if not entries:
            console.print("[yellow]No prompts found[/yellow]")
            return
            
        table = Table(title=f"Logged Prompts ({len(entries)} shown)")
        table.add_column("ID", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Model", style="blue")
        table.add_column("Timestamp", style="yellow")
        
        for entry in entries:
            prompt_preview = entry.prompt[:50] + "..." if len(entry.prompt) > 50 else entry.prompt
            table.add_row(
                str(entry.id),
                entry.agent,
                entry.model,
                entry.timestamp.isoformat(),
            )
            if verbose:
                console.print(f"  Prompt: {prompt_preview}")
                
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def export(
    output: Path = typer.Argument(..., help="Output file path"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    format: str = typer.Option("jsonl", "--format", "-f", help="Export format (jsonl, json, csv)"),
) -> None:
    """Export prompts to a file."""
    try:
        entries = logger.list_prompts(agent=agent, limit=10000)
        
        if format == "jsonl":
            with open(output, "w") as f:
                for entry in entries:
                    f.write(entry.model_dump_json() + "\n")
        elif format == "json":
            with open(output, "w") as f:
                json.dump([entry.model_dump() for entry in entries], f, indent=2, default=str)
        else:
            console.print(f"[red]Unsupported format:[/red] {format}")
            raise typer.Exit(1)
            
        console.print(f"[green]✓[/green] Exported {len(entries)} prompts to {output}")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def stats() -> None:
    """Show statistics about logged prompts."""
    try:
        stats = logger.get_stats()
        
        table = Table(title="Prompt Logger Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            table.add_row(key.replace("_", " ").title(), str(value))
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
