"""Export commands — CSV/JSON export of trade history and settlements."""

import csv
import io
import json
import typer
from typing import Optional
from datetime import datetime, timedelta
from rich.console import Console

from ..client import KalshiClient
from ..exceptions import AuthenticationError

console = Console()


def export_fills(
    output: str = typer.Option("fills.csv", "--output", "-o", help="Output file path"),
    ticker: Optional[str] = typer.Option(None, "--ticker", "-t", help="Filter by ticker"),
    fmt: str = typer.Option("csv", "--format", "-f", help="Output format: csv or json"),
    limit: int = typer.Option(500, "--limit", "-l", help="Max fills to export"),
):
    """Export trade history (fills) to CSV or JSON.

    Examples:
        kalshi export-fills
        kalshi export-fills --output my_trades.csv
        kalshi export-fills --ticker INXD-25DEC31-T8150 --format json -o trades.json
    """
    client = KalshiClient()

    try:
        # Paginate to get all fills up to limit
        all_fills = []
        cursor = None
        while len(all_fills) < limit:
            batch_size = min(100, limit - len(all_fills))
            fills = client.get_fills(ticker=ticker, limit=batch_size, cursor=cursor)
            if not fills:
                break
            all_fills.extend(fills)
            # No cursor available from the list response, break after first batch
            break
    except AuthenticationError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    if not all_fills:
        console.print("[dim]No fills to export[/dim]")
        return

    rows = []
    for f in all_fills:
        rows.append({
            "date": f.created_time.isoformat() if f.created_time else "",
            "ticker": f.ticker,
            "side": f.side,
            "action": f.action,
            "quantity": f.count,
            "yes_price": f.yes_price,
            "no_price": f.no_price,
            "cost_usd": f"{(f.price * f.count) / 100:.2f}",
            "is_taker": f.is_taker,
            "trade_id": f.trade_id,
            "order_id": f.order_id or "",
        })

    if fmt == "json":
        if not output.endswith(".json"):
            output = output.rsplit(".", 1)[0] + ".json"
        with open(output, "w") as fp:
            json.dump({"fills": rows, "exported_at": datetime.now().isoformat()}, fp, indent=2)
    else:
        if not output.endswith(".csv"):
            output = output.rsplit(".", 1)[0] + ".csv"
        with open(output, "w", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    console.print(f"[green]Exported {len(rows)} fills to {output}[/green]")


def export_settlements(
    output: str = typer.Option("settlements.csv", "--output", "-o", help="Output file path"),
    days: int = typer.Option(365, "--days", "-d", help="Days of history"),
    ticker: Optional[str] = typer.Option(None, "--ticker", "-t", help="Filter by ticker"),
    fmt: str = typer.Option("csv", "--format", "-f", help="Output format: csv or json"),
):
    """Export settlement history to CSV or JSON.

    Useful for tax reporting and performance analysis.

    Examples:
        kalshi export-settlements
        kalshi export-settlements --days 30 --format json
        kalshi export-settlements -o taxes_2025.csv --days 365
    """
    client = KalshiClient()

    min_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    try:
        settlements = client.get_settlements(min_ts=min_ts, ticker=ticker, limit=100)
    except AuthenticationError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    if not settlements:
        console.print("[dim]No settlements to export[/dim]")
        return

    rows = []
    for s in settlements:
        position = s.position
        side = "YES" if position > 0 else "NO"
        qty = abs(position)

        rows.append({
            "date": s.settled_time.isoformat() if s.settled_time else "",
            "ticker": s.ticker,
            "side": side,
            "quantity": qty,
            "result": s.market_result,
            "won": s.won,
            "revenue_usd": f"{s.revenue_dollars:.2f}",
        })

    if fmt == "json":
        if not output.endswith(".json"):
            output = output.rsplit(".", 1)[0] + ".json"
        with open(output, "w") as fp:
            json.dump({"settlements": rows, "exported_at": datetime.now().isoformat()}, fp, indent=2)
    else:
        if not output.endswith(".csv"):
            output = output.rsplit(".", 1)[0] + ".csv"
        with open(output, "w", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    console.print(f"[green]Exported {len(rows)} settlements to {output}[/green]")
