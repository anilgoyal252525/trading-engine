from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import OrderSide, OrderType, TradeStatus


@dataclass
class Tick:
    symbol: str
    ltp: float
    timestamp: datetime
    volume: int = 0
    bid: float = 0.0
    ask: float = 0.0


@dataclass
class Candle:
    symbol: str
    timeframe: int          # minutes — e.g. 30 for 30-min candle
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime     # candle open time
    is_closed: bool = False

    def __post_init__(self) -> None:
        if self.high < self.open or self.high < self.close:
            raise ValueError("Candle high must be >= open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("Candle low must be <= open and close")


@dataclass
class Signal:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float = 0.0      # relevant for LIMIT / SL
    sl: float = 0.0
    target: float = 0.0
    tag: str = ""


@dataclass
class TradeData:
    trade_id: str
    strategy_id: str
    symbol: str
    side: OrderSide
    quantity: int
    entry_price: float
    status: TradeStatus = TradeStatus.PENDING
    exit_price: float = 0.0
    sl: float = 0.0
    target: float = 0.0
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    order_id: str = ""
    tag: str = ""

    def compute_pnl(self) -> float:
        if self.exit_price == 0.0:
            return 0.0
        multiplier = 1 if self.side == OrderSide.BUY else -1
        self.pnl = multiplier * (self.exit_price - self.entry_price) * self.quantity
        return self.pnl