"""Price alert commands — set and check price alerts."""

import time
import typer
import json
from typing import Optional
from rich.console import Console
from rich.table import Table

from ..client import KalshiClient
from ..storage import get_alerts, add_alert, remove_alert, mark_alert_triggered, clear_alerts
from ..display import format_price

console = Console()


def alert_add(
    ticker: str = typer.Argument(..., help="Market ticker"),
    above: Optional[int] = typer.Option(None, "--above", help="Alert when YES price rises above this (cents)"),
    below: Optional[int] = typer.Option(None, "--below", help="Alert when YES price drops below this (cents)"),
    side: str = typer.Option("yes", "--side", "-s", help="Side to monitor: yes or no"),
):
    """Set a price alert on a market.

    Examples:
        kalshi alert-add INXD-25DEC31-T8150 --above 60
        kalshi alert-add INXD-25DEC31-T8150 --below 30
        kalshi alert-add INXD-25DEC31-T8150 --above 60 --below 30
    """
    if above is None and below is None:
        console.print("[red]Error: specify --above and/or --below[/red]")
        raise typer.Exit(1)

    # Validate ticker
    client = KalshiClient(auth=None)
    try:
        client.get_market(ticker)
    except Exception:
        console.print(f"[red]Market '{ticker}' not found[/red]")
        raise typer.Exit(1)

    alert = add_alert(ticker, side=side, above=above, below=below)
    conditions = []
    if above:
        conditions.append(f"above {above}c")
    if below:
        conditions.append(f"below {below}c")
    console.print(f"[green]Alert #{alert['id']} set: {ticker} {side.upper()} {' or '.join(conditions)}[/green]")


def alert_list(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all price alerts.

    Examples:
        kalshi alerts
    """
    alerts = get_alerts()
    if not alerts:
        console.print("[dim]No alerts set. Use: kalshi alert-add <TICKER> --above/--below[/dim]")
        return

    if json_output:
        print(json.dumps({"alerts": alerts}, indent=2))
        return

    table = Table(title=f"Price Alerts ({len(alerts)})")
    table.add_column("ID", style="dim")
    table.add_column("Ticker", style="cyan")
    table.add_column("Side", style="yellow")
    table.add_column("Above", justify="right", style="green")
    table.add_column("Below", justify="right", style="red")
    table.add_column("Status")

    for a in alerts:
        status = "[green]Active[/green]" if not a.get("triggered") else "[dim]Triggered[/dim]"
        table.add_row(
            str(a["id"]),
            a["ticker"],
            a["side"].upper(),
            format_price(a.get("above")),
            format_price(a.get("below")),
            status,
        )

    console.print(table)


def alert_remove(
    alert_id: int = typer.Argument(..., help="Alert ID to remove"),
):
    """Remove a price alert.

    Examples:
        kalshi alert-rm 1
    """
    if remove_alert(alert_id):
        console.print(f"[green]Alert #{alert_id} removed[/green]")
    else:
        console.print(f"[red]Alert #{alert_id} not found[/red]")


def alert_check():
    """Check all active alerts against current prices.

    Prints triggered alerts and marks them.

    Examples:
        kalshi alert-check
    """
    alerts = get_alerts()
    active = [a for a in alerts if not a.get("triggered")]

    if not active:
        console.print("[dim]No active alerts[/dim]")
        return

    # Group by ticker to minimize API calls
    tickers = set(a["ticker"] for a in active)
    client = KalshiClient(auth=None)

    prices = {}
    for ticker in tickers:
        try:
            m = client.get_market(ticker)
            prices[ticker] = {"yes_bid": m.yes_bid, "yes_ask": m.yes_ask, "no_bid": m.no_bid, "no_ask": m.no_ask}
        except Exception:
            pass

    triggered_count = 0
    for a in active:
        ticker = a["ticker"]
        if ticker not in prices:
            continue

        p = prices[ticker]
        side = a.get("side", "yes")
        current = p.get(f"{side}_bid") or 0

        fired = False
        if a.get("above") and current >= a["above"]:
            fired = True
        if a.get("below") and current <= a["below"]:
            fired = True

        if fired:
            triggered_count += 1
            mark_alert_triggered(a["id"])
            console.print(f"[bold red]ALERT #{a['id']}:[/bold red] {ticker} {side.upper()} is at {current}c")

    if triggered_count == 0:
        console.print(f"[dim]Checked {len(active)} alerts — none triggered[/dim]")
    else:
        console.print(f"\n[bold]{triggered_count} alert(s) triggered[/bold]")


def alert_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear all alerts."""
    alerts = get_alerts()
    if not alerts:
        console.print("[dim]No alerts to clear[/dim]")
        return

    if not force:
        confirm = typer.confirm(f"Remove all {len(alerts)} alerts?")
        if not confirm:
            raise typer.Exit(0)

    clear_alerts()
    console.print(f"[green]Cleared {len(alerts)} alerts[/green]")
