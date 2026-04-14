"""Watchlist commands — save and monitor favorite markets."""

import typer
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..client import KalshiClient
from ..storage import get_watchlist, add_to_watchlist, remove_from_watchlist, clear_watchlist
from ..display import format_price, format_volume, sparkline_with_color

console = Console()


def watch(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show current prices for all watchlist tickers.

    Examples:
        kalshi watch
        kalshi watch --json
    """
    tickers = get_watchlist()
    if not tickers:
        console.print("[dim]Watchlist is empty. Add tickers with: kalshi watch-add <TICKER>[/dim]")
        return

    client = KalshiClient(auth=None)

    rows = []
    for ticker in tickers:
        try:
            m = client.get_market(ticker)
            # Fetch recent trades for sparkline
            spark = ""
            try:
                trades_resp = client.get_trades(ticker, limit=20)
                prices = [t.yes_price for t in reversed(trades_resp.trades)]
                if prices:
                    spark = sparkline_with_color(prices)
            except Exception:
                pass

            rows.append({
                "ticker": ticker,
                "title": m.title,
                "status": m.status,
                "yes_bid": m.yes_bid,
                "yes_ask": m.yes_ask,
                "volume_24h": m.volume_24h,
                "last_price": m.last_price,
                "previous_price": m.previous_price,
                "sparkline": spark,
            })
        except Exception:
            rows.append({
                "ticker": ticker,
                "title": "???",
                "status": "error",
                "yes_bid": None,
                "yes_ask": None,
                "volume_24h": 0,
                "last_price": None,
                "previous_price": None,
                "sparkline": "",
            })

    if json_output:
        print(json.dumps({"watchlist": rows}, indent=2))
        return

    table = Table(title=f"Watchlist ({len(rows)} markets)")
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Title", max_width=30)
    table.add_column("Bid", justify="right", style="green")
    table.add_column("Ask", justify="right", style="green")
    table.add_column("Last", justify="right")
    table.add_column("Chg", justify="right")
    table.add_column("Trend", min_width=8)
    table.add_column("24h Vol", justify="right", style="dim")

    for r in rows:
        change = ""
        if r["last_price"] is not None and r["previous_price"] is not None:
            diff = r["last_price"] - r["previous_price"]
            color = "green" if diff >= 0 else "red"
            change = f"[{color}]{diff:+d}c[/{color}]"

        table.add_row(
            r["ticker"],
            (r["title"][:30] + "...") if len(r["title"]) > 30 else r["title"],
            format_price(r["yes_bid"]),
            format_price(r["yes_ask"]),
            format_price(r["last_price"]),
            change,
            r.get("sparkline", ""),
            format_volume(r["volume_24h"]),
        )

    console.print(table)


def watch_add(
    ticker: str = typer.Argument(..., help="Market ticker to add"),
):
    """Add a ticker to your watchlist.

    Examples:
        kalshi watch-add INXD-25DEC31-T8150
    """
    # Validate the ticker exists
    client = KalshiClient(auth=None)
    try:
        client.get_market(ticker)
    except Exception:
        console.print(f"[red]Market '{ticker}' not found[/red]")
        raise typer.Exit(1)

    if add_to_watchlist(ticker):
        console.print(f"[green]Added {ticker} to watchlist[/green]")
    else:
        console.print(f"[yellow]{ticker} is already in watchlist[/yellow]")


def watch_remove(
    ticker: str = typer.Argument(..., help="Market ticker to remove"),
):
    """Remove a ticker from your watchlist.

    Examples:
        kalshi watch-rm INXD-25DEC31-T8150
    """
    if remove_from_watchlist(ticker):
        console.print(f"[green]Removed {ticker} from watchlist[/green]")
    else:
        console.print(f"[yellow]{ticker} is not in watchlist[/yellow]")


def watch_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear the entire watchlist."""
    tickers = get_watchlist()
    if not tickers:
        console.print("[dim]Watchlist is already empty[/dim]")
        return

    if not force:
        confirm = typer.confirm(f"Remove all {len(tickers)} tickers from watchlist?")
        if not confirm:
            raise typer.Exit(0)

    clear_watchlist()
    console.print(f"[green]Cleared {len(tickers)} tickers from watchlist[/green]")
