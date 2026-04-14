"""Analytics commands — win rate, ROI, and performance stats."""

import json
import typer
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..client import KalshiClient
from ..display import format_pnl
from ..exceptions import AuthenticationError

console = Console()


def stats(
    days: int = typer.Option(90, "--days", "-d", help="Days of history to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Trading performance statistics.

    Analyzes your settlement history to show win rate, average return,
    best/worst trades, and more.

    Examples:
        kalshi stats
        kalshi stats --days 30
        kalshi stats --json
    """
    client = KalshiClient()

    min_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    try:
        settlements = client.get_settlements(min_ts=min_ts, limit=100)
        fills = client.get_fills(limit=500)
    except AuthenticationError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    if not settlements:
        console.print(f"[dim]No settlements in the last {days} days[/dim]")
        return

    # Core stats
    total_trades = len(settlements)
    wins = [s for s in settlements if s.won]
    losses = [s for s in settlements if not s.won]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    total_revenue = sum(s.revenue_dollars for s in settlements)
    win_revenue = sum(s.revenue_dollars for s in wins) if wins else 0
    loss_revenue = sum(s.revenue_dollars for s in losses) if losses else 0

    avg_win = win_revenue / win_count if win_count > 0 else 0
    avg_loss = loss_revenue / loss_count if loss_count > 0 else 0

    # Best and worst
    best = max(settlements, key=lambda s: s.revenue_dollars)
    worst = min(settlements, key=lambda s: s.revenue_dollars)

    # Profit factor
    gross_profit = sum(s.revenue_dollars for s in settlements if s.revenue_dollars > 0)
    gross_loss = abs(sum(s.revenue_dollars for s in settlements if s.revenue_dollars < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Category breakdown
    categories: dict[str, dict] = {}
    for s in settlements:
        # Extract category from ticker prefix
        cat = s.ticker.split("-")[0] if "-" in s.ticker else s.ticker
        if cat not in categories:
            categories[cat] = {"wins": 0, "losses": 0, "pnl": 0.0}
        if s.won:
            categories[cat]["wins"] += 1
        else:
            categories[cat]["losses"] += 1
        categories[cat]["pnl"] += s.revenue_dollars

    # Fill stats
    total_contracts = sum(f.count for f in fills)
    buy_fills = [f for f in fills if f.action == "buy"]
    sell_fills = [f for f in fills if f.action == "sell"]
    taker_fills = [f for f in fills if f.is_taker]
    maker_pct = ((len(fills) - len(taker_fills)) / len(fills) * 100) if fills else 0

    result = {
        "period_days": days,
        "total_settled": total_trades,
        "wins": win_count,
        "losses": loss_count,
        "win_rate_pct": round(win_rate, 1),
        "total_pnl": round(total_revenue, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "best_trade": {"ticker": best.ticker, "pnl": round(best.revenue_dollars, 2)},
        "worst_trade": {"ticker": worst.ticker, "pnl": round(worst.revenue_dollars, 2)},
        "total_fills": len(fills),
        "total_contracts": total_contracts,
        "maker_pct": round(maker_pct, 1),
    }

    if json_output:
        print(json.dumps(result, indent=2))
        return

    # Display
    console.print(Panel(f"[bold]Trading Stats (last {days} days)[/bold]"))

    console.print(f"\n[bold]Settlement Record[/bold]")
    console.print(f"  Settled: {total_trades}  |  Won: [green]{win_count}[/green]  |  Lost: [red]{loss_count}[/red]")

    # Win rate bar
    bar_width = 30
    win_chars = int(win_rate / 100 * bar_width)
    bar = f"[green]{'#' * win_chars}[/green][red]{'#' * (bar_width - win_chars)}[/red]"
    console.print(f"  Win Rate: {bar} {win_rate:.1f}%")

    console.print(f"\n[bold]P&L[/bold]")
    console.print(f"  Total P&L: {format_pnl(total_revenue)}")
    console.print(f"  Avg Win:   {format_pnl(avg_win)}")
    console.print(f"  Avg Loss:  {format_pnl(avg_loss)}")
    pf_color = "green" if profit_factor >= 1.0 else "red"
    console.print(f"  Profit Factor: [{pf_color}]{profit_factor:.2f}x[/{pf_color}]")

    console.print(f"\n[bold]Best / Worst[/bold]")
    console.print(f"  Best:  {best.ticker} {format_pnl(best.revenue_dollars)}")
    console.print(f"  Worst: {worst.ticker} {format_pnl(worst.revenue_dollars)}")

    # Category table
    if categories:
        console.print()
        cat_table = Table(title="By Ticker Prefix")
        cat_table.add_column("Prefix", style="cyan")
        cat_table.add_column("W", justify="right", style="green")
        cat_table.add_column("L", justify="right", style="red")
        cat_table.add_column("P&L", justify="right")

        sorted_cats = sorted(categories.items(), key=lambda x: x[1]["pnl"], reverse=True)
        for cat, data in sorted_cats[:10]:
            cat_table.add_row(
                cat,
                str(data["wins"]),
                str(data["losses"]),
                format_pnl(data["pnl"]),
            )
        console.print(cat_table)

    # Fill stats
    if fills:
        console.print(f"\n[bold]Execution[/bold]")
        console.print(f"  Total Fills: {len(fills)}  |  Contracts: {total_contracts}")
        console.print(f"  Maker Rate: {maker_pct:.0f}%")
