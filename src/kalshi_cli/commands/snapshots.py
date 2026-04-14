"""Portfolio snapshot commands — track P&L over time."""

import json
import typer
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..client import KalshiClient
from ..storage import get_snapshots, save_snapshot
from ..display import format_pnl
from ..exceptions import AuthenticationError

console = Console()


def snapshot_take():
    """Take a portfolio snapshot (balance + positions).

    Run this daily to track your portfolio over time.

    Examples:
        kalshi snapshot
    """
    client = KalshiClient()

    try:
        bal = client.get_balance()
        positions = client.get_positions()
    except AuthenticationError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    active = [p for p in positions if p.position != 0]
    total_exposure = sum(p.exposure_dollars for p in active)
    total_realized = sum(p.realized_pnl_dollars for p in active)

    # Calculate unrealized P&L
    total_unrealized = 0.0
    for pos in active:
        try:
            m = client.get_market(pos.ticker)
            current = m.yes_bid if pos.side == "yes" else m.no_bid
            fills = client.get_fills(ticker=pos.ticker, limit=100)
            avg_entry = client.calculate_avg_entry(fills, pos.side)
            if avg_entry > 0 and current:
                total_unrealized += (current - avg_entry) * pos.quantity / 100
        except Exception:
            pass

    snap = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "balance": bal.balance_dollars,
        "available": bal.available_dollars,
        "positions_count": len(active),
        "total_exposure": round(total_exposure, 2),
        "total_realized_pnl": round(total_realized, 2),
        "total_unrealized_pnl": round(total_unrealized, 2),
        "net_value": round(bal.balance_dollars + total_unrealized, 2),
    }

    save_snapshot(snap)
    console.print(f"[green]Snapshot saved[/green]")
    console.print(f"  Balance: ${snap['balance']:.2f}")
    console.print(f"  Positions: {snap['positions_count']}")
    console.print(f"  Unrealized P&L: {format_pnl(snap['total_unrealized_pnl'])}")
    console.print(f"  Net Value: ${snap['net_value']:.2f}")


def snapshot_history(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to show"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show portfolio value history from snapshots.

    Examples:
        kalshi pnl
        kalshi pnl --days 7
        kalshi pnl --json
    """
    snapshots = get_snapshots()
    if not snapshots:
        console.print("[dim]No snapshots yet. Run: kalshi snapshot[/dim]")
        return

    # Filter to requested window
    recent = snapshots[-days:]

    if json_output:
        print(json.dumps({"snapshots": recent}, indent=2))
        return

    table = Table(title=f"Portfolio History (last {len(recent)} snapshots)")
    table.add_column("Date", style="dim")
    table.add_column("Balance", justify="right", style="green")
    table.add_column("Positions", justify="right")
    table.add_column("Exposure", justify="right")
    table.add_column("Unrealized", justify="right")
    table.add_column("Net Value", justify="right", style="bold")
    table.add_column("", min_width=10)

    prev_value = None
    for s in recent:
        net = s.get("net_value", s.get("balance", 0))
        change = ""
        if prev_value is not None:
            diff = net - prev_value
            color = "green" if diff >= 0 else "red"
            change = f"[{color}]{diff:+.2f}[/{color}]"
        prev_value = net

        # Sparkline-style bar
        bar = _mini_bar(s.get("total_unrealized_pnl", 0))

        table.add_row(
            s.get("date", ""),
            f"${s.get('balance', 0):.2f}",
            str(s.get("positions_count", 0)),
            f"${s.get('total_exposure', 0):.2f}",
            format_pnl(s.get("total_unrealized_pnl", 0)),
            f"${net:.2f}",
            bar,
        )

    console.print(table)

    # Summary
    if len(recent) >= 2:
        first_val = recent[0].get("net_value", recent[0].get("balance", 0))
        last_val = recent[-1].get("net_value", recent[-1].get("balance", 0))
        total_change = last_val - first_val
        console.print(f"\n[bold]Period change:[/bold] {format_pnl(total_change)}")


def _mini_bar(value: float, width: int = 10) -> str:
    """Create a mini bar chart for a value."""
    if value == 0:
        return "[dim]-[/dim]"
    max_val = 10.0  # $10 scale
    clamped = max(-max_val, min(max_val, value))
    chars = int(abs(clamped) / max_val * width) or 1
    if value > 0:
        return f"[green]{'#' * chars}[/green]"
    else:
        return f"[red]{'#' * chars}[/red]"
