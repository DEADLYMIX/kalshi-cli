"""Profile commands — switch between demo and live environments."""

import os
import typer
from rich.console import Console
from rich.table import Table

from ..storage import get_profiles, get_active_profile, set_active_profile

console = Console()


def profile_list():
    """List available profiles (demo/live).

    Examples:
        kalshi profiles
    """
    profiles = get_profiles()
    active = os.getenv("KALSHI_PROFILE", get_active_profile())

    table = Table(title="Profiles")
    table.add_column("", width=2)
    table.add_column("Name", style="cyan")
    table.add_column("URL")
    table.add_column("Description")

    for name, info in profiles.items():
        marker = "[green]*[/green]" if name == active else " "
        table.add_row(
            marker,
            name,
            info.get("base_url", ""),
            info.get("description", ""),
        )

    console.print(table)
    console.print(f"\n[dim]Active: {active}[/dim]")
    console.print(f"[dim]Switch with: kalshi profile-set <name>[/dim]")
    console.print(f"[dim]Or set KALSHI_PROFILE=demo in your environment[/dim]")


def profile_set(
    name: str = typer.Argument(..., help="Profile name: live or demo"),
):
    """Switch active profile.

    This sets the default profile. You can also override per-command
    with the KALSHI_PROFILE environment variable.

    Create ~/.kalshi/demo.env with your demo API credentials to use
    separate keys for each environment.

    Examples:
        kalshi profile-set demo
        kalshi profile-set live
    """
    profiles = get_profiles()
    if name not in profiles:
        console.print(f"[red]Unknown profile: {name}[/red]")
        console.print(f"[dim]Available: {', '.join(profiles.keys())}[/dim]")
        raise typer.Exit(1)

    set_active_profile(name)
    info = profiles[name]
    console.print(f"[green]Switched to profile: {name}[/green]")
    console.print(f"  URL: {info.get('base_url', '')}")
    console.print(f"  {info.get('description', '')}")

    if name == "demo":
        console.print(f"\n[yellow]Tip: Create ~/.kalshi/demo.env with your demo API keys[/yellow]")


def profile_current():
    """Show which profile is currently active.

    Examples:
        kalshi profile
    """
    active = os.getenv("KALSHI_PROFILE", get_active_profile())
    profiles = get_profiles()
    info = profiles.get(active, {})

    source = "KALSHI_PROFILE env var" if os.getenv("KALSHI_PROFILE") else "saved setting"
    console.print(f"[bold]Active profile:[/bold] [cyan]{active}[/cyan] (from {source})")
    console.print(f"  URL: {info.get('base_url', 'default')}")
    console.print(f"  {info.get('description', '')}")
