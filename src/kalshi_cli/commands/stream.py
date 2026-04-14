"""Streaming commands — real-time price feeds via websocket or polling."""

import time
import json
import typer
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table

from ..client import KalshiClient
from ..display import format_price, format_volume

console = Console()


def stream(
    tickers: str = typer.Argument(..., help="Comma-separated tickers to stream"),
    interval: int = typer.Option(5, "--interval", "-i", help="Refresh interval in seconds"),
    duration: int = typer.Option(0, "--duration", "-d", help="Stop after N seconds (0 = forever)"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON lines"),
):
    """Stream live prices for one or more markets.

    Polls the API at the specified interval and displays a live-updating table.
    Press Ctrl+C to stop.

    Examples:
        kalshi stream TICKER1,TICKER2
        kalshi stream TICKER1 --interval 2
        kalshi stream TICKER1,TICKER2 --json
        kalshi stream TICKER1 --duration 60
    """
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        console.print("[red]Error: no tickers provided[/red]")
        raise typer.Exit(1)

    client = KalshiClient(auth=None)
    start_time = time.time()

    # Track previous prices for change detection
    prev_prices: dict[str, Optional[int]] = {}

    if json_output:
        _stream_json(client, ticker_list, interval, duration, start_time)
        return

    console.print(f"[dim]Streaming {len(ticker_list)} markets every {interval}s. Ctrl+C to stop.[/dim]\n")

    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                table = _build_stream_table(client, ticker_list, prev_prices)
                live.update(table)

                if duration > 0 and (time.time() - start_time) >= duration:
                    break

                time.sleep(interval)
    except KeyboardInterrupt:
        elapsed = int(time.time() - start_time)
        console.print(f"\n[dim]Streamed for {elapsed}s[/dim]")


def _build_stream_table(
    client: KalshiClient,
    tickers: list[str],
    prev_prices: dict,
) -> Table:
    now = datetime.now().strftime("%H:%M:%S")
    table = Table(title=f"Live Prices ({now})")
    table.add_column("Ticker", style="cyan", no_wrap=True)
    table.add_column("Yes Bid", justify="right")
    table.add_column("Yes Ask", justify="right")
    table.add_column("Chg", justify="right")
    table.add_column("Spread", justify="right", style="dim")
    table.add_column("Volume", justify="right", style="dim")

    for ticker in tickers:
        try:
            m = client.get_market(ticker)
            current = m.yes_bid
            prev = prev_prices.get(ticker)

            change = ""
            if prev is not None and current is not None:
                diff = current - prev
                if diff != 0:
                    color = "green" if diff > 0 else "red"
                    arrow = "^" if diff > 0 else "v"
                    change = f"[{color}]{arrow}{abs(diff)}c[/{color}]"

            prev_prices[ticker] = current

            spread = ""
            if m.yes_ask and m.yes_bid:
                spread = f"{m.yes_ask - m.yes_bid}c"

            bid_str = f"[green]{m.yes_bid}c[/green]" if m.yes_bid else "-"
            ask_str = f"[green]{m.yes_ask}c[/green]" if m.yes_ask else "-"

            table.add_row(
                ticker,
                bid_str,
                ask_str,
                change,
                spread,
                format_volume(m.volume_24h),
            )
        except Exception:
            table.add_row(ticker, "[red]err[/red]", "", "", "", "")

    return table


def _stream_json(
    client: KalshiClient,
    tickers: list[str],
    interval: int,
    duration: int,
    start_time: float,
) -> None:
    try:
        while True:
            for ticker in tickers:
                try:
                    m = client.get_market(ticker)
                    print(json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "ticker": ticker,
                        "yes_bid": m.yes_bid,
                        "yes_ask": m.yes_ask,
                        "no_bid": m.no_bid,
                        "no_ask": m.no_ask,
                        "volume_24h": m.volume_24h,
                        "last_price": m.last_price,
                    }), flush=True)
                except Exception as e:
                    print(json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "ticker": ticker,
                        "error": str(e),
                    }), flush=True)

            if duration > 0 and (time.time() - start_time) >= duration:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
