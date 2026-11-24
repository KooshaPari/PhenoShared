"""CLI interface for thegent-cli-share."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from thegent_cli_share import __version__
from thegent_cli_share.adapters.dedup import InMemoryLockAdapter
from thegent_cli_share.adapters.queue import InMemoryQueueAdapter
from thegent_cli_share.domain.entities import TaskQueueItem, QueuePriority
from thegent_cli_share.domain.value_objects import CommandHash

app = typer.Typer(help="CLI share system - command deduplication and task queue")
console = Console()

# Global adapters (in-memory for CLI)
_lock_adapter = InMemoryLockAdapter()
_queue_adapter = InMemoryQueueAdapter()


@app.command()
def lock_acquire(
    cmd_hash: str = typer.Argument(..., help="Command hash to lock"),
    pid: int = typer.Option(0, help="Process ID"),
    output_path: Optional[str] = typer.Option(None, help="Output file path"),
) -> None:
    """Acquire a command lock."""
    try:
        lock = _lock_adapter.acquire(CommandHash(cmd_hash), pid, output_path)
        console.print(f"[green]Lock acquired:[/green] {lock.cmd_hash} (PID: {lock.pid})")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def lock_release(
    cmd_hash: str = typer.Argument(..., help="Command hash to release"),
    pid: int = typer.Option(..., help="Process ID"),
) -> None:
    """Release a command lock."""
    try:
        _lock_adapter.release(CommandHash(cmd_hash), pid)
        console.print(f"[green]Lock released:[/green] {cmd_hash}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="lock-list")
def lock_list() -> None:
    """List all active locks."""
    locks = _lock_adapter.list_all()
    if not locks:
        console.print("[yellow]No active locks[/yellow]")
        return

    table = Table(title="Active Locks")
    table.add_column("Command Hash", style="cyan")
    table.add_column("PID", style="magenta")
    table.add_column("Status", style="green")

    for lock in locks:
        table.add_row(lock.cmd_hash, str(lock.pid), lock.status.value)

    console.print(table)


@app.command()
def queue_enqueue(
    command: str = typer.Argument(..., help="Command to enqueue"),
    priority: str = typer.Option("normal", help="Priority: low, normal, high, critical"),
) -> None:
    """Enqueue a task."""
    item = _queue_adapter.enqueue(TaskQueueItem(command=command, priority=QueuePriority(priority)))
    console.print(f"[green]Task enqueued:[/green] {item.id} ({priority})")


@app.command(name="queue-list")
def queue_list() -> None:
    """List all queued tasks."""
    items = _queue_adapter.list_all()
    if not items:
        console.print("[yellow]Queue is empty[/yellow]")
        return

    table = Table(title=f"Task Queue ({len(items)} items)")
    table.add_column("ID", style="cyan")
    table.add_column("Command", style="white")
    table.add_column("Priority", style="yellow")
    table.add_column("Status", style="green")

    for item in items:
        table.add_row(str(item.id), item.command[:50], item.priority.value, item.status)

    console.print(table)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"thegent-cli-share [cyan]{__version__}[/cyan]")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
