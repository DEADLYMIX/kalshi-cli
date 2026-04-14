"""Pydantic models for Kalshi API entities."""

from datetime import datetime
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator


def _dollars_to_cents(v: Optional[str]) -> Optional[int]:
    """Convert a dollar string like '0.4700' to integer cents (47)."""
    if v is None or v == "" or v == "0.0000":
        return None
    try:
        return int(round(float(v) * 100))
    except (ValueError, TypeError):
        return None


def _fp_to_int(v: Optional[str]) -> int:
    """Convert a floating-point string like '133915.88' to int."""
    if v is None or v == "":
        return 0
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return 0


# === Market Models ===


class Market(BaseModel):
    """A prediction market on Kalshi."""

    ticker: str
    title: str
    subtitle: Optional[str] = None
    status: Literal["open", "closed", "settled", "active", "inactive", "finalized"] = "open"
    # Integer cents (legacy) or None
    yes_ask: Optional[int] = None
    yes_bid: Optional[int] = None
    no_ask: Optional[int] = None
    no_bid: Optional[int] = None
    # Dollar-string fields (current API)
    yes_ask_dollars: Optional[str] = None
    yes_bid_dollars: Optional[str] = None
    no_ask_dollars: Optional[str] = None
    no_bid_dollars: Optional[str] = None
    last_price_dollars: Optional[str] = None
    previous_price_dollars: Optional[str] = None
    previous_yes_ask_dollars: Optional[str] = None
    previous_yes_bid_dollars: Optional[str] = None
    # Volume fields — int (legacy) or fp string (current)
    volume: int = 0
    volume_24h: int = 0
    volume_fp: Optional[str] = None
    volume_24h_fp: Optional[str] = None
    open_interest: int = 0
    open_interest_fp: Optional[str] = None
    close_time: Optional[datetime] = None
    expiration_time: Optional[datetime] = None
    result: Optional[Literal["yes", "no", "all_yes", "all_no"]] = None
    rules_primary: Optional[str] = None
    rules_secondary: Optional[str] = None
    event_ticker: Optional[str] = None
    series_ticker: Optional[str] = None
    category: Optional[str] = None
    last_price: Optional[int] = None
    previous_price: Optional[int] = None
    previous_yes_ask: Optional[int] = None
    previous_yes_bid: Optional[int] = None

    model_config = {"extra": "allow"}

    @field_validator("result", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> Any:
        """Convert empty string to None for result field."""
        if v == "":
            return None
        return v

    def model_post_init(self, __context: Any) -> None:
        """Normalize dollar-string fields to integer cents for uniform access."""
        if self.yes_ask is None and self.yes_ask_dollars:
            self.yes_ask = _dollars_to_cents(self.yes_ask_dollars)
        if self.yes_bid is None and self.yes_bid_dollars:
            self.yes_bid = _dollars_to_cents(self.yes_bid_dollars)
        if self.no_ask is None and self.no_ask_dollars:
            self.no_ask = _dollars_to_cents(self.no_ask_dollars)
        if self.no_bid is None and self.no_bid_dollars:
            self.no_bid = _dollars_to_cents(self.no_bid_dollars)
        if self.last_price is None and self.last_price_dollars:
            self.last_price = _dollars_to_cents(self.last_price_dollars)
        if self.previous_price is None and self.previous_price_dollars:
            self.previous_price = _dollars_to_cents(self.previous_price_dollars)
        if self.previous_yes_ask is None and self.previous_yes_ask_dollars:
            self.previous_yes_ask = _dollars_to_cents(self.previous_yes_ask_dollars)
        if self.previous_yes_bid is None and self.previous_yes_bid_dollars:
            self.previous_yes_bid = _dollars_to_cents(self.previous_yes_bid_dollars)
        if self.volume == 0 and self.volume_fp:
            self.volume = _fp_to_int(self.volume_fp)
        if self.volume_24h == 0 and self.volume_24h_fp:
            self.volume_24h = _fp_to_int(self.volume_24h_fp)
        if self.open_interest == 0 and self.open_interest_fp:
            self.open_interest = _fp_to_int(self.open_interest_fp)

    @property
    def spread(self) -> Optional[int]:
        """Calculate bid-ask spread in cents."""
        if self.yes_ask and self.yes_bid:
            return self.yes_ask - self.yes_bid
        return None

    @property
    def midpoint(self) -> Optional[float]:
        """Calculate midpoint price in cents."""
        if self.yes_ask and self.yes_bid:
            return (self.yes_ask + self.yes_bid) / 2
        return None


class OrderBookLevel(BaseModel):
    """A single price level in the order book."""

    price: int  # cents
    quantity: int


class OrderBook(BaseModel):
    """Order book for a market."""

    ticker: str
    yes_bids: list[OrderBookLevel] = Field(default_factory=list)
    no_bids: list[OrderBookLevel] = Field(default_factory=list)

    @property
    def best_yes_bid(self) -> Optional[int]:
        return self.yes_bids[0].price if self.yes_bids else None

    @property
    def best_no_bid(self) -> Optional[int]:
        return self.no_bids[0].price if self.no_bids else None

    @property
    def best_yes_ask(self) -> Optional[int]:
        """YES ask = 100 - NO bid."""
        return 100 - self.best_no_bid if self.best_no_bid else None

    @property
    def best_no_ask(self) -> Optional[int]:
        """NO ask = 100 - YES bid."""
        return 100 - self.best_yes_bid if self.best_yes_bid else None


class Event(BaseModel):
    """An event containing multiple related markets."""

    event_ticker: str
    title: str
    subtitle: Optional[str] = None
    category: Optional[str] = None
    series_ticker: Optional[str] = None
    mutually_exclusive: bool = False
    markets: list[Market] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class Series(BaseModel):
    """A recurring series of events (e.g., monthly CPI)."""

    ticker: str
    title: str
    category: Optional[str] = None
    contract_url: Optional[str] = None  # Rules PDF

    model_config = {"extra": "allow"}


# === Portfolio Models ===


class Balance(BaseModel):
    """Account balance information."""

    balance: int  # cents
    available_balance: Optional[int] = None  # cents

    model_config = {"extra": "allow"}

    @property
    def balance_dollars(self) -> float:
        return self.balance / 100

    @property
    def available_dollars(self) -> float:
        if self.available_balance is not None:
            return self.available_balance / 100
        return self.balance_dollars


class Position(BaseModel):
    """A position in a market."""

    ticker: str
    position: int  # positive = YES, negative = NO
    market_exposure: int = 0  # cents
    realized_pnl: int = 0  # cents
    resting_orders_count: int = 0
    total_traded: int = 0

    model_config = {"extra": "allow"}

    @property
    def side(self) -> Literal["yes", "no"]:
        return "yes" if self.position > 0 else "no"

    @property
    def quantity(self) -> int:
        return abs(self.position)

    @property
    def exposure_dollars(self) -> float:
        return self.market_exposure / 100

    @property
    def realized_pnl_dollars(self) -> float:
        return self.realized_pnl / 100


class Order(BaseModel):
    """An order (resting, executed, or canceled)."""

    order_id: str
    ticker: str
    side: Literal["yes", "no"]
    action: Literal["buy", "sell"]
    type: Literal["limit", "market"]
    status: Literal["resting", "executed", "canceled", "pending"]
    count: int = Field(alias="count", default=0)
    remaining_count: int = 0
    fill_count: int = 0
    yes_price: Optional[int] = None
    no_price: Optional[int] = None
    created_time: Optional[datetime] = None
    expiration_time: Optional[datetime] = None

    model_config = {"extra": "allow", "populate_by_name": True}

    @property
    def price(self) -> Optional[int]:
        """Get the relevant price for this order's side."""
        return self.yes_price if self.side == "yes" else self.no_price


class Fill(BaseModel):
    """A trade execution."""

    trade_id: str
    ticker: str
    side: Literal["yes", "no"]
    action: Literal["buy", "sell"]
    count: int
    yes_price: int
    no_price: int
    is_taker: bool = False
    created_time: Optional[datetime] = None
    order_id: Optional[str] = None

    model_config = {"extra": "allow"}

    @property
    def price(self) -> int:
        return self.yes_price if self.side == "yes" else self.no_price


class Settlement(BaseModel):
    """A settled position."""

    ticker: str
    position: int = Field(alias="settled_contracts", default=0)
    market_result: Literal["yes", "no", "all_yes", "all_no"]
    revenue: int  # cents
    settled_time: Optional[datetime] = None

    model_config = {"extra": "allow", "populate_by_name": True}

    @property
    def won(self) -> bool:
        if self.market_result in ("yes", "all_yes"):
            return self.position > 0
        return self.position < 0

    @property
    def revenue_dollars(self) -> float:
        return self.revenue / 100


class Trade(BaseModel):
    """A public trade (market activity)."""

    trade_id: str
    ticker: str
    # API returns count_fp (string) or count (int) depending on version
    count: int = 0
    count_fp: Optional[str] = None
    # API returns yes_price (int cents) or yes_price_dollars (string) depending on version
    yes_price: int = 0
    yes_price_dollars: Optional[str] = None
    no_price: Optional[int] = None
    no_price_dollars: Optional[str] = None
    taker_side: Optional[Literal["yes", "no"]] = None
    created_time: Optional[datetime] = None

    model_config = {"extra": "allow"}

    def model_post_init(self, __context: Any) -> None:
        # Normalize dollar-string fields to integer cents
        if self.yes_price == 0 and self.yes_price_dollars:
            self.yes_price = int(float(self.yes_price_dollars) * 100)
        if self.no_price is None and self.no_price_dollars:
            self.no_price = int(float(self.no_price_dollars) * 100)
        if self.count == 0 and self.count_fp:
            self.count = int(float(self.count_fp))


class Candlestick(BaseModel):
    """OHLC price data for a time period."""

    end_period_ts: int
    open: int
    high: int
    low: int
    close: int
    volume: int = 0

    @property
    def open_price(self) -> float:
        """Open price in dollars."""
        return self.open / 100

    @property
    def close_price(self) -> float:
        """Close price in dollars."""
        return self.close / 100


# === API Response Wrappers ===


class MarketsResponse(BaseModel):
    """Response from get markets endpoint."""

    markets: list[Market]
    cursor: Optional[str] = None


class EventsResponse(BaseModel):
    """Response from get events endpoint."""

    events: list[Event]
    cursor: Optional[str] = None


class PositionsResponse(BaseModel):
    """Response from get positions endpoint."""

    market_positions: list[Position]
    cursor: Optional[str] = None


class OrdersResponse(BaseModel):
    """Response from get orders endpoint."""

    orders: list[Order]
    cursor: Optional[str] = None


class FillsResponse(BaseModel):
    """Response from get fills endpoint."""

    fills: list[Fill]
    cursor: Optional[str] = None


class TradesResponse(BaseModel):
    """Response from get trades endpoint."""

    trades: list[Trade]
    cursor: Optional[str] = None


class SettlementsResponse(BaseModel):
    """Response from get settlements endpoint."""

    settlements: list[Settlement]
    cursor: Optional[str] = None


class ExchangeStatus(BaseModel):
    """Exchange status information."""

    trading_active: bool
    exchange_active: bool

    model_config = {"extra": "allow"}


class CreateOrderResponse(BaseModel):
    """Response from create order endpoint."""

    order: Order


class CancelOrderResponse(BaseModel):
    """Response from cancel order endpoint."""

    order: Order
    reduced_by: int = 0
