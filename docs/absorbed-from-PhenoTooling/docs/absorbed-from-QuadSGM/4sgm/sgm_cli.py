"""4SGM CLI - Typer-based command interface."""

import subprocess
import sys
import typer

app = typer.Typer(
    name="4sgm",
    help="4SGM - LangGraph + MCP Server",
    rich_markup_mode="rich",
)


@app.command()
def mcp(
    port: int = typer.Option(3000, "--port", "-p", help="MCP server port"),
):
    """Start MCP server."""
    typer.echo("[bold blue]🚀 Starting MCP Server...[/bold blue]")
    typer.echo(f"  Port: {port}")
    typer.echo("  Tools: 25+\n")

    try:
        subprocess.run(
            [sys.executable, "-m", "fastmcp", "run", "4sgm.mcp_server.server:mcp"],
            check=True,
        )
    except KeyboardInterrupt:
        typer.echo("\n[yellow]⊘ Interrupted[/yellow]")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        typer.echo(f"[red]✗ Failed: {e}[/red]")
        sys.exit(1)


@app.command()
def api(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="API host"),
    port: int = typer.Option(8000, "--port", "-p", help="API port"),
    reload: bool = typer.Option(
        True, "--reload/--no-reload", help="Enable auto-reload"
    ),
):
    """Start FastAPI server."""
    typer.echo("[bold blue]🚀 Starting FastAPI Server...[/bold blue]")
    typer.echo(f"  Host: {host}")
    typer.echo(f"  Port: {port}")
    typer.echo(f"  Docs: http://localhost:{port}/docs\n")

    try:
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "4sgm.backend.app:app",
            "--host",
            host,
            "--port",
            str(port),
        ]
        if reload:
            cmd.append("--reload")

        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        typer.echo("\n[yellow]⊘ Interrupted[/yellow]")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        typer.echo(f"[red]✗ Failed: {e}[/red]")
        sys.exit(1)


@app.command()
def test():
    """Run integration tests."""
    typer.echo("[bold blue]🧪 Running Tests...[/bold blue]\n")

    try:
        subprocess.run(
            [sys.executable, "4sgm/backend/test_mcp_integration.py"],
            check=True,
        )
    except KeyboardInterrupt:
        typer.echo("\n[yellow]⊘ Interrupted[/yellow]")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        typer.echo(f"[red]✗ Failed: {e}[/red]")
        sys.exit(1)


@app.command()
def tools():
    """List available MCP tools."""
    typer.echo("[bold blue]🛠️  Available MCP Tools (25+):[/bold blue]\n")

    tools_dict = {
        "Product": [
            "get_product",
            "search_products",
            "get_inventory",
            "update_inventory",
            "get_pricing",
            "apply_discount",
        ],
        "Cart": [
            "create_cart",
            "add_to_cart",
            "remove_from_cart",
            "calculate_cart_total",
            "validate_cart",
            "create_order",
        ],
        "Shipping": [
            "calculate_shipping",
            "get_shipping_methods",
            "track_shipment",
            "estimate_delivery",
        ],
        "Pricing": [
            "get_bulk_pricing",
            "apply_coupon",
            "get_promotions",
            "calculate_savings",
        ],
        "Customer": [
            "get_customer_history",
            "get_customer_preferences",
            "save_customer_preferences",
        ],
        "RFQ": [
            "create_rfq",
            "get_rfq_status",
            "accept_rfq",
        ],
    }

    for category, tool_list in tools_dict.items():
        typer.echo(f"[bold]{category}:[/bold]")
        for tool in tool_list:
            typer.echo(f"  • [green]{tool}[/green]")
        typer.echo()


@app.command()
def dev():
    """Show development setup instructions."""
    typer.echo("[bold blue]📚 Development Setup[/bold blue]\n")
    typer.echo("Run in separate terminals:\n")
    typer.echo("  [bold]Terminal 1:[/bold] [green]4sgm mcp[/green]")
    typer.echo("  [bold]Terminal 2:[/bold] [green]4sgm api[/green]")
    typer.echo("  [bold]Terminal 3:[/bold] [green]4sgm test[/green]\n")
    typer.echo("Or use:")
    typer.echo("  [green]4sgm api --help[/green]  - See API options")
    typer.echo("  [green]4sgm mcp --help[/green]  - See MCP options\n")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
