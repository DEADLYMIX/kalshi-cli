"""Order template commands — save and reuse common order configurations."""

import typer
import json
from typing import Optional
from rich.console import Console
from rich.table import Table

from ..storage import get_templates, save_template, remove_template

console = Console()


def template_save(
    name: str = typer.Argument(..., help="Template name"),
    ticker: str = typer.Option(..., "--ticker", "-t", help="Market ticker"),
    side: str = typer.Option(..., "--side", "-s", help="yes or no"),
    action: str = typer.Option(..., "--action", "-a", help="buy or sell"),
    count: int = typer.Option(..., "--count", "-c", help="Number of contracts"),
    price: Optional[int] = typer.Option(None, "--price", "-p", help="Limit price"),
    order_type: str = typer.Option("market", "--type", help="limit or market"),
):
    """Save an order template for quick reuse.

    Examples:
        kalshi template-save scalp-spy -t INXD-25DEC31-T8150 -s yes -a buy -c 10 --type limit -p 45
        kalshi template-save quick-cpi -t KXCPI-25JAN -s yes -a buy -c 5
    """
    template = {
        "ticker": ticker,
        "side": side.lower(),
        "action": action.lower(),
        "count": count,
        "order_type": order_type.lower(),
        "price": price,
    }

    save_template(name, template)
    console.print(f"[green]Template '{name}' saved[/green]")
    _display_template(name, template)


def template_list(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all saved order templates.

    Examples:
        kalshi templates
    """
    templates = get_templates()
    if not templates:
        console.print("[dim]No templates saved. Use: kalshi template-save <name> ...[/dim]")
        return

    if json_output:
        print(json.dumps({"templates": templates}, indent=2))
        return

    table = Table(title=f"Order Templates ({len(templates)})")
    table.add_column("Name", style="cyan")
    table.add_column("Ticker", style="dim")
    table.add_column("Side", style="yellow")
    table.add_column("Action")
    table.add_column("Count", justify="right")
    table.add_column("Type")
    table.add_column("Price", justify="right")

    for name, t in templates.items():
        action_color = "green" if t["action"] == "buy" else "red"
        table.add_row(
            name,
            t["ticker"],
            t["side"].upper(),
            f"[{action_color}]{t['action'].upper()}[/{action_color}]",
            str(t["count"]),
            t["order_type"],
            f"{t['price']}c" if t.get("price") else "market",
        )

    console.print(table)


def template_remove(
    name: str = typer.Argument(..., help="Template name to remove"),
):
    """Remove a saved order template.

    Examples:
        kalshi template-rm scalp-spy
    """
    if remove_template(name):
        console.print(f"[green]Template '{name}' removed[/green]")
    else:
        console.print(f"[red]Template '{name}' not found[/red]")


def template_run(
    name: str = typer.Argument(..., help="Template name to execute"),
    ticker: Optional[str] = typer.Option(None, "--ticker", "-t", help="Override ticker"),
    count: Optional[int] = typer.Option(None, "--count", "-c", help="Override count"),
    price: Optional[int] = typer.Option(None, "--price", "-p", help="Override price"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Execute a saved order template.

    You can override individual fields when running a template.

    Examples:
        kalshi quick scalp-spy
        kalshi quick scalp-spy --ticker INXD-25JAN01-T8500
        kalshi quick scalp-spy --count 20 --force
    """
    from .trading import order_cmd

    templates = get_templates()
    if name not in templates:
        console.print(f"[red]Template '{name}' not found[/red]")
        console.print("[dim]Available templates:[/dim]")
        for t_name in templates:
            console.print(f"  [cyan]{t_name}[/cyan]")
        raise typer.Exit(1)

    t = templates[name]
    console.print(f"[dim]Running template: {name}[/dim]")

    order_cmd(
        ticker=ticker or t["ticker"],
        side=t["side"],
        action=t["action"],
        count=count or t["count"],
        order_type=t.get("order_type", "market"),
        price=price if price is not None else t.get("price"),
        force=force,
    )


def _display_template(name: str, t: dict) -> None:
    action_color = "green" if t["action"] == "buy" else "red"
    console.print(f"  [{action_color}]{t['action'].upper()}[/{action_color}] "
                  f"{t['count']} [yellow]{t['side'].upper()}[/yellow] "
                  f"on [cyan]{t['ticker']}[/cyan] "
                  f"@ {t['price']}c" if t.get("price") else f"  [{action_color}]{t['action'].upper()}[/{action_color}] "
                  f"{t['count']} [yellow]{t['side'].upper()}[/yellow] "
                  f"on [cyan]{t['ticker']}[/cyan] @ market")
