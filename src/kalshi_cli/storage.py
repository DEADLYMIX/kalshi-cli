"""Local JSON-file storage for watchlists, alerts, snapshots, and templates.

All data lives under ~/.kalshi/data/ as simple JSON files.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


DATA_DIR = Path.home() / ".kalshi" / "data"


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load(name: str) -> dict:
    _ensure_dir()
    path = DATA_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save(name: str, data: dict) -> None:
    _ensure_dir()
    path = DATA_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, default=str))


# === Watchlist ===


def get_watchlist() -> list[str]:
    data = _load("watchlist")
    return data.get("tickers", [])


def add_to_watchlist(ticker: str) -> bool:
    tickers = get_watchlist()
    if ticker in tickers:
        return False
    tickers.append(ticker)
    _save("watchlist", {"tickers": tickers})
    return True


def remove_from_watchlist(ticker: str) -> bool:
    tickers = get_watchlist()
    if ticker not in tickers:
        return False
    tickers.remove(ticker)
    _save("watchlist", {"tickers": tickers})
    return True


def clear_watchlist() -> None:
    _save("watchlist", {"tickers": []})


# === Price Alerts ===


def get_alerts() -> list[dict]:
    data = _load("alerts")
    return data.get("alerts", [])


def add_alert(
    ticker: str,
    side: str = "yes",
    above: Optional[int] = None,
    below: Optional[int] = None,
) -> dict:
    alerts = get_alerts()
    alert = {
        "id": len(alerts) + 1,
        "ticker": ticker,
        "side": side,
        "above": above,
        "below": below,
        "created": datetime.now().isoformat(),
        "triggered": False,
    }
    alerts.append(alert)
    _save("alerts", {"alerts": alerts})
    return alert


def remove_alert(alert_id: int) -> bool:
    alerts = get_alerts()
    new_alerts = [a for a in alerts if a["id"] != alert_id]
    if len(new_alerts) == len(alerts):
        return False
    _save("alerts", {"alerts": new_alerts})
    return True


def mark_alert_triggered(alert_id: int) -> None:
    alerts = get_alerts()
    for a in alerts:
        if a["id"] == alert_id:
            a["triggered"] = True
            break
    _save("alerts", {"alerts": alerts})


def clear_alerts() -> None:
    _save("alerts", {"alerts": []})


# === Portfolio Snapshots ===


def get_snapshots() -> list[dict]:
    data = _load("snapshots")
    return data.get("snapshots", [])


def save_snapshot(snapshot: dict) -> None:
    snapshots = get_snapshots()
    snapshots.append(snapshot)
    # Keep last 365 snapshots
    if len(snapshots) > 365:
        snapshots = snapshots[-365:]
    _save("snapshots", {"snapshots": snapshots})


# === Order Templates ===


def get_templates() -> dict[str, dict]:
    data = _load("templates")
    return data.get("templates", {})


def save_template(name: str, template: dict) -> None:
    templates = get_templates()
    templates[name] = template
    _save("templates", {"templates": templates})


def remove_template(name: str) -> bool:
    templates = get_templates()
    if name not in templates:
        return False
    del templates[name]
    _save("templates", {"templates": templates})
    return True


# === Profiles ===


def get_profiles() -> dict[str, dict]:
    data = _load("profiles")
    return data.get("profiles", {
        "live": {
            "base_url": "https://api.elections.kalshi.com/trade-api/v2",
            "description": "Live trading",
        },
        "demo": {
            "base_url": "https://demo-api.kalshi.co/trade-api/v2",
            "description": "Demo/paper trading",
        },
    })


def get_active_profile() -> str:
    data = _load("profiles")
    return data.get("active", "live")


def set_active_profile(name: str) -> None:
    data = _load("profiles")
    if "profiles" not in data:
        data["profiles"] = get_profiles()
    data["active"] = name
    _save("profiles", data)
