"""
Run: pytest tests/test_phase4.py -v
"""
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

import pytest

from src.core.data_model import Candle, TradeData
from src.core.enums import OrderSide, TradeStatus
from src.strategies.strategy_one.config import StrategyOneParams
from src.strategies.strategy_one.logic import compute_entry, compute_exit
from src.strategies.strategy_one.handler import Handler
from src.infrastructure.config_loader import StrategyConfig, SymbolConfig


def make_candle(open_, high, low, close, symbol="NSE:NIFTY50-INDEX", tf=30):
    return Candle(
        symbol=symbol, timeframe=tf,
        open=open_, high=high, low=low, close=close,
        volume=1000,
        timestamp=datetime(2024, 1, 1, 9, 15),
        is_closed=True,
    )


# ------------------------------------------------------------------ #
#  Pure logic tests
# ------------------------------------------------------------------ #

def test_entry_not_enough_history():
    params = StrategyOneParams()
    candle = make_candle(22000, 22100, 21950, 22050)
    result = compute_entry(candle, [], params)
    assert result is None


def test_entry_no_breakout():
    params = StrategyOneParams(entry_buffer_pts=5.0)
    prev = make_candle(21900, 22000, 21850, 21950)
    candle = make_candle(22000, 22003, 21980, 22002)
    result = compute_entry(candle, [prev, prev], params)
    assert result is None  # close 22002 < prev_high 22000 + 5 = 22005


def test_entry_breakout_fires():
    params = StrategyOneParams(entry_buffer_pts=5.0)
    prev = make_candle(21900, 22000, 21850, 21950)
    candle = make_candle(22000, 22100, 21990, 22010)
    result = compute_entry(candle, [prev, prev], params)
    assert result is not None
    assert result.side == OrderSide.BUY


def test_exit_sl_hit():
    params = StrategyOneParams()
    trade = TradeData(
        trade_id="T1", strategy_id="S1",
        symbol="NSE:NIFTY50-INDEX", side=OrderSide.BUY,
        quantity=50, entry_price=22000.0, sl=21900.0,
    )
    candle = make_candle(21950, 21980, 21880, 21900)  # low=21880 < sl=21900
    result = compute_exit(candle, trade, params)
    assert result is not None
    assert result.tag == "SL_HIT"


def test_exit_target_hit():
    params = StrategyOneParams()
    trade = TradeData(
        trade_id="T1", strategy_id="S1",
        symbol="NSE:NIFTY50-INDEX", side=OrderSide.BUY,
        quantity=50, entry_price=22000.0, sl=21900.0, target=22300.0,
    )
    candle = make_candle(22100, 22350, 22080, 22200)  # high=22350 > target=22300
    result = compute_exit(candle, trade, params)
    assert result is not None
    assert result.tag == "TARGET_HIT"


# ------------------------------------------------------------------ #
#  Handler (integration)
# ------------------------------------------------------------------ #

def make_strategy_config():
    return StrategyConfig(
        id="STRATEGY_ONE",
        module="strategy_one",
        enabled=True,
        max_trades=1,
        symbols=[SymbolConfig(name="NSE:NIFTY50-INDEX", mode="candle", timeframe=30)],
        params={"fast_period": 9, "slow_period": 21, "entry_buffer_pts": 5.0},
    )


@pytest.mark.asyncio
async def test_handler_on_candle_entry():
    from src.managers.trade_state_manager import TradeStateManager
    from src.managers.order_placement_manager import OrderPlacementManager
    from src.managers.candle_manager import CandleManager

    class MockBroker:
        is_connected = True
        async def place_order(self, sig): return "ORD_001"
        async def cancel_order(self, oid): return True
        async def get_order_status(self, oid): return {}
        async def get_positions(self): return []
        async def connect(self): pass
        async def disconnect(self): pass

    tsm = TradeStateManager()
    opm = OrderPlacementManager(MockBroker(), tsm)
    cm = CandleManager()

    handler = Handler(make_strategy_config())
    handler.wire(opm, tsm, cm)
    await handler.start()

    # Build history first (need ≥ 2 candles)
    prev1 = make_candle(21900, 22000, 21850, 21950)
    prev2 = make_candle(21950, 22050, 21920, 22000)
    handler._history["NSE:NIFTY50-INDEX"] = [prev1, prev2]

    # Trigger a breakout candle
    breakout = make_candle(22010, 22150, 22000, 22050)  # close > 22000+5
    await handler.on_candle(breakout)

    assert tsm.open_trade_count("STRATEGY_ONE") == 1


@pytest.mark.asyncio
async def test_handler_max_trades_respected():
    from src.managers.trade_state_manager import TradeStateManager
    from src.managers.order_placement_manager import OrderPlacementManager
    from src.managers.candle_manager import CandleManager

    class MockBroker:
        is_connected = True
        async def place_order(self, sig): return "ORD_002"
        async def cancel_order(self, oid): return True
        async def get_order_status(self, oid): return {}
        async def get_positions(self): return []
        async def connect(self): pass
        async def disconnect(self): pass

    tsm = TradeStateManager()
    opm = OrderPlacementManager(MockBroker(), tsm)
    cm = CandleManager()

    handler = Handler(make_strategy_config())  # max_trades = 1
    handler.wire(opm, tsm, cm)
    await handler.start()

    prev1 = make_candle(21900, 22000, 21850, 21950)
    prev2 = make_candle(21950, 22050, 21920, 22000)
    handler._history["NSE:NIFTY50-INDEX"] = [prev1, prev2]

    breakout = make_candle(22010, 22150, 22000, 22050)
    await handler.on_candle(breakout)
    await handler.on_candle(breakout)  # second call should NOT open another trade

    assert tsm.open_trade_count("STRATEGY_ONE") == 1  # still 1