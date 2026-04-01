from __future__ import annotations

from typing import List, Optional

from ...core.data_model import Candle, Signal, TradeData
from ...core.enums import OrderSide, OrderType
from .config import StrategyOneParams


def compute_entry(
    candle: Candle,
    history: List[Candle],
    params: StrategyOneParams,
) -> Optional[Signal]:
    """
    Pure function: given the latest closed candle and history,
    return a Signal or None.
    No side effects, no I/O — just logic.

    Replace this with your real entry condition.
    Example: breakout above previous high.
    """
    if len(history) < 2:
        return None

    prev_high = history[-2].high
    if candle.close > prev_high + params.entry_buffer_pts:
        return Signal(
            symbol=candle.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1,   # TODO: load from config or position sizer
            sl=candle.low - 10,
            tag="BREAKOUT_ENTRY",
        )
    return None


def compute_exit(
    candle: Candle,
    trade: TradeData,
    params: StrategyOneParams,
) -> Optional[Signal]:
    """
    Pure function: given the latest closed candle and open trade,
    return an exit Signal or None.
    """
    # SL hit
    if candle.low <= trade.sl:
        return Signal(
            symbol=candle.symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=trade.quantity,
            price=trade.sl,
            tag="SL_HIT",
        )
    # Target hit
    if trade.target > 0 and candle.high >= trade.target:
        return Signal(
            symbol=candle.symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=trade.quantity,
            price=trade.target,
            tag="TARGET_HIT",
        )
    return None