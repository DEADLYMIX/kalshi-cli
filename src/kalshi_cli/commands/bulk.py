"""Bulk trading commands — operate on multiple markets at once."""

import sys
import typer
import json
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..client import KalshiClient
from ..display import format_price
from ..exceptions import AuthenticationError, NotFoundError, APIError

console = Console()


def bulk_buy(
    side: str = typer.Argument(..., help="yes or no"),
    count: int = typer.Argument(..., help="Contracts per market"),
    tickers: str = typer.Argument(..., help="Comma-separated tickers"),
    price: Optional[int] = typer.Option(None, "--price", "-p", help="Limit price (same for all)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Buy contracts across multiple markets at once.

    Examples:
        kalshi bulk-buy yes 10 TICKER1,TICKER2,TICKER3
        kalshi bulk-buy no 5 TICKER1,TICKER2 --price 30
        kalshi bulk-buy yes 10 TICKER1,TICKER2,TICKER3 --force
    """
    _bulk_order("buy", side, count, tickers.split(","), price, force)


def bulk_sell(
    side: str = typer.Argument(..., help="yes or no"),
    count: int = typer.Argument(..., help="Contracts per market"),
    tickers: str = typer.Argument(..., help="Comma-separated tickers"),
    price: Optional[int] = typer.Option(None, "--price", "-p", help="Limit price (same for all)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Sell contracts across multiple markets at once.

    Examples:
        kalshi bulk-sell yes 10 TICKER1,TICKER2,TICKER3
    """
    _bulk_order("sell", side, count, tickers.split(","), price, force)


def _bulk_order(
    action: str,
    side: str,
    count: int,
    tickers: list[str],
    price: Optional[int],
    force: bool,
) -> None:
    side = side.lower()
    if side not in ("yes", "no"):
        console.print("[red]Error: side must be 'yes' or 'no'[/red]")
        raise typer.Exit(1)

    if count < 1:
        console.print("[red]Error: count must be at least 1[/red]")
        raise typer.Exit(1)

    tickers = [t.strip() for t in tickers if t.strip()]
    if not tickers:
        console.print("[red]Error: no tickers provided[/red]")
        raise typer.Exit(1)

    client = KalshiClient()

    # Fetch all markets first
    markets_data = {}
    for ticker in tickers:
        try:
            m = client.get_market(ticker)
            markets_data[ticker] = m
        except NotFoundError:
            console.print(f"[red]Market '{ticker}' not found — skipping[/red]")
        except Exception as e:
            console.print(f"[red]Error fetching '{ticker}': {e} — skipping[/red]")

    if not markets_data:
        console.print("[red]No valid markets found[/red]")
        raise typer.Exit(1)

    # Show preview
    order_type = "limit" if price else "market"
    action_color = "green" if action == "buy" else "red"

    table = Table(title="Bulk Order Preview")
    table.add_column("Ticker", style="cyan")
    table.add_column("Action")
    table.add_column("Side", style="yellow")
    table.add_column("Count", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Current", justify="right", style="dim")

    total_cost_est = 0
    order_prices = {}

    for ticker, m in markets_data.items():
        if price:
            op = price
        elif action == "buy":
            op = (m.yes_ask if side == "yes" else m.no_ask) or 0
        else:
            op = (m.yes_bid if side == "yes" else m.no_bid) or 0

        if not op:
            console.print(f"[yellow]Warning: No liquidity for {ticker} — will skip[/yellow]")
            continue

        order_prices[ticker] = op
        total_cost_est += op * count / 100

        current = (m.yes_bid if side == "yes" else m.no_bid) or 0
        table.add_row(
            ticker,
            f"[{action_color}]{action.upper()}[/{action_color}]",
            side.upper(),
            str(count),
            f"{op}c",
            f"{current}c",
        )

    console.print(table)
    console.print(f"\n[bold]Total markets:[/bold] {len(order_prices)}")
    console.print(f"[bold]Est. total cost:[/bold] ${total_cost_est:.2f}")

    if not order_prices:
        console.print("[red]No orders to place[/red]")
        raise typer.Exit(1)

    if not force:
        if not sys.stdin.isatty():
            console.print("[red]Error: Cannot prompt in non-interactive mode. Use --force.[/red]")
            raise typer.Exit(1)
        confirm = typer.confirm(f"Place {len(order_prices)} orders?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    # Execute
    success = 0
    failed = 0
    for ticker, op in order_prices.items():
        try:
            order = client.create_order(
                ticker=ticker,
                side=side,
                action=action,
                count=count,
                price=op,
                order_type=order_type,
            )
            console.print(f"  [green]OK[/green] {ticker} — {order.status}")
            success += 1
        except APIError as e:
            console.print(f"  [red]FAIL[/red] {ticker} — {e.message}")
            failed += 1

    console.print(f"\n[bold]Results:[/bold] [green]{success} succeeded[/green], [red]{failed} failed[/red]")
