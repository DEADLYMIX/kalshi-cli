"""Kalshi CLI - Command Line Interface for Kalshi prediction markets."""

import typer

from .commands import (
    reference,
    markets,
    portfolio,
    trading,
    watchlist,
    alerts,
    export,
    snapshots,
    analytics,
    templates,
    bulk,
    profiles,
    stream,
)

app = typer.Typer(
    name="kalshi",
    help="Kalshi CLI - Trade prediction markets from the command line.",
    no_args_is_help=True,
)


# === Market Commands ===
app.command(name="markets")(markets.markets)
app.command(name="market")(markets.market)
app.command(name="find")(markets.find)
app.command(name="orderbook")(markets.orderbook)
app.command(name="rules")(markets.rules)
app.command(name="series")(markets.series_cmd)
app.command(name="events")(markets.events)
app.command(name="event")(markets.event)
app.command(name="trades")(markets.trades)
app.command(name="history")(markets.history)


# === Portfolio Commands ===
app.command(name="balance")(portfolio.balance)
app.command(name="positions")(portfolio.positions)
app.command(name="orders")(portfolio.orders)
app.command(name="fills")(portfolio.fills)
app.command(name="status")(portfolio.status_cmd)
app.command(name="settlements")(portfolio.settlements)
app.command(name="summary")(portfolio.summary)


# === Trading Commands ===
app.command(name="order")(trading.order_cmd)
app.command(name="cancel")(trading.cancel)
app.command(name="buy")(trading.buy)
app.command(name="sell")(trading.sell)
app.command(name="close")(trading.close_position)
app.command(name="cancel-all")(trading.cancel_all)


# === Watchlist Commands ===
app.command(name="watch")(watchlist.watch)
app.command(name="watch-add")(watchlist.watch_add)
app.command(name="watch-rm")(watchlist.watch_remove)
app.command(name="watch-clear")(watchlist.watch_clear)


# === Alert Commands ===
app.command(name="alert-add")(alerts.alert_add)
app.command(name="alerts")(alerts.alert_list)
app.command(name="alert-rm")(alerts.alert_remove)
app.command(name="alert-check")(alerts.alert_check)
app.command(name="alert-clear")(alerts.alert_clear)


# === Export Commands ===
app.command(name="export-fills")(export.export_fills)
app.command(name="export-settlements")(export.export_settlements)


# === Snapshot & P&L Commands ===
app.command(name="snapshot")(snapshots.snapshot_take)
app.command(name="pnl")(snapshots.snapshot_history)


# === Analytics Commands ===
app.command(name="stats")(analytics.stats)


# === Template Commands ===
app.command(name="template-save")(templates.template_save)
app.command(name="templates")(templates.template_list)
app.command(name="template-rm")(templates.template_remove)
app.command(name="quick")(templates.template_run)


# === Bulk Commands ===
app.command(name="bulk-buy")(bulk.bulk_buy)
app.command(name="bulk-sell")(bulk.bulk_sell)


# === Profile Commands ===
app.command(name="profiles")(profiles.profile_list)
app.command(name="profile-set")(profiles.profile_set)
app.command(name="profile")(profiles.profile_current)


# === Streaming Commands ===
app.command(name="stream")(stream.stream)


# === Reference Commands ===
app.command(name="endpoints")(reference.endpoints)
app.command(name="show")(reference.show)
app.command(name="schema")(reference.schema_cmd)
app.command(name="schemas")(reference.schemas_cmd)
app.command(name="curl")(reference.curl)
app.command(name="api-search")(reference.api_search)
app.command(name="tags")(reference.tags_cmd)
app.command(name="quickref")(reference.quickref)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
