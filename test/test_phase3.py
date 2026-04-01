"""
Run: pytest tests/test_phase3.py -v
"""
from datetime import datetime
import asyncio

import pytest

from src.core.data_model import Candle, Signal, Tick, TradeData
from src.core.enums import OrderSide, OrderType, TradeStatus
from src.managers.candle_manager import CandleManager, TimeframeCandleBuilder
from src.managers.symbol_manager import SymbolManager
from src.managers.trade_state_manager import TradeStateManager
from src.managers.order_placement_manager import OrderPlacementManager


# ------------------------------------------------------------------ #
#  CandleBuilder
# ------------------------------------------------------------------ #

def make_tick(ltp: float, hour: int, minute: int) -> Tick:
    return Tick(
        symbol="NSE:NIFTY50-INDEX",
        ltp=ltp,
        timestamp=datetime(2024, 1, 1, hour, minute, 0),
        volume=100,
    )


def test_candle_builder_first_tick():
    builder = TimeframeCandleBuilder("NSE:NIFTY50-INDEX", 30)
    closed = builder.update(make_tick(22000.0, 9, 15))
    assert closed is None  # no previous bar to close
    cur = builder.get_current()
    assert cur.open == 22000.0
    assert cur.close == 22000.0


def test_candle_builder_closes_bar():
    builder = TimeframeCandleBuilder("NSE:NIFTY50-INDEX", 30)
    builder.update(make_tick(22000.0, 9, 15))
    builder.update(make_tick(22200.0, 9, 20))
    builder.update(make_tick(21900.0, 9, 25))
    # New bar
    closed = builder.update(make_tick(22100.0, 9, 45))
    assert closed is not None
    assert closed.is_closed is True
    assert closed.high == 22200.0
    assert closed.low == 21900.0


def test_candle_manager_fires_callback():
    received = []
    cm = CandleManager()
    cm.register("NSE:NIFTY50-INDEX", 30, lambda c: received.append(c))

    cm.on_tick(make_tick(22000.0, 9, 15))
    cm.on_tick(make_tick(22100.0, 9, 20))
    cm.on_tick(make_tick(22050.0, 9, 45))  # triggers close of 9:15 bar

    assert len(received) == 1
    assert received[0].symbol == "NSE:NIFTY50-INDEX"
    assert received[0].is_closed is True


# ------------------------------------------------------------------ #
#  TradeStateManager
# ------------------------------------------------------------------ #

def make_trade(strategy_id="S1") -> TradeData:
    return TradeData(
        trade_id="",
        strategy_id=strategy_id,
        symbol="NSE:NIFTY50-INDEX",
        side=OrderSide.BUY,
        quantity=50,
        entry_price=22000.0,
    )


def test_create_trade_assigns_id():
    tsm = TradeStateManager()
    t = tsm.create_trade(make_trade())
    assert t.trade_id != ""


def test_open_trade_count():
    tsm = TradeStateManager()
    tsm.create_trade(make_trade("S1"))
    tsm.create_trade(make_trade("S1"))
    tsm.create_trade(make_trade("S2"))
    assert tsm.open_trade_count("S1") == 2
    assert tsm.open_trade_count("S2") == 1


def test_close_trade_computes_pnl():
    tsm = TradeStateManager()
    t = tsm.create_trade(make_trade())
    tsm.update_status(t.trade_id, TradeStatus.OPEN)
    closed = tsm.close_trade(t.trade_id, exit_price=22300.0)
    assert closed.status == TradeStatus.CLOSED
    assert closed.pnl == 15000.0  # 300 * 50


# ------------------------------------------------------------------ #
#  OrderPlacementManager (mock broker)
# ------------------------------------------------------------------ #

class MockOrderBroker:
    is_connected = True
    async def place_order(self, signal): return "ORDER_001"
    async def cancel_order(self, order_id): return True
    async def get_order_status(self, order_id): return {}
    async def get_positions(self): return []
    async def connect(self): pass
    async def disconnect(self): pass


@pytest.mark.asyncio
async def test_order_placement_creates_trade():
    tsm = TradeStateManager()
    opm = OrderPlacementManager(MockOrderBroker(), tsm)
    sig = Signal("NSE:NIFTY50-INDEX", OrderSide.BUY, OrderType.MARKET, 50)

    trade = await opm.place(sig, strategy_id="S1")
    assert trade.status == TradeStatus.OPEN
    assert trade.order_id == "ORDER_001"


@pytest.mark.asyncio
async def test_order_placement_tracks_count():
    tsm = TradeStateManager()
    opm = OrderPlacementManager(MockOrderBroker(), tsm)
    sig = Signal("NSE:NIFTY50-INDEX", OrderSide.BUY, OrderType.MARKET, 50)

    await opm.place(sig, "S1")
    await opm.place(sig, "S1")
    assert tsm.open_trade_count("S1") == 2