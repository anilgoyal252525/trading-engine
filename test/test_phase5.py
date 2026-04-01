"""
Run: pytest tests/test_phase5.py -v
Integration test: Engine wires up and starts cleanly with mock brokers.
"""
import asyncio
import pytest

from src.infrastructure.config_loader import (
    AppConfig, BrokerConfig, StrategyConfig, SymbolConfig
)
from src.engine import Engine
import src.broker  # noqa — trigger registration


class MockDataBroker:
    is_connected = False
    async def connect(self): self.is_connected = True
    async def disconnect(self): self.is_connected = False
    async def subscribe(self, symbols, callback): pass
    async def unsubscribe(self, symbols): pass
    async def get_historical_candles(self, *a): return []


class MockOrderBroker:
    is_connected = False
    async def connect(self): self.is_connected = True
    async def disconnect(self): self.is_connected = False
    async def place_order(self, sig): return "MOCK_ID"
    async def cancel_order(self, oid): return True
    async def get_order_status(self, oid): return {}
    async def get_positions(self): return []


def make_test_config():
    return AppConfig(
        brokers=BrokerConfig(data="fyers", order="fyers"),
        strategies=[
            StrategyConfig(
                id="STRATEGY_ONE",
                module="strategy_one",
                enabled=True,
                max_trades=1,
                symbols=[SymbolConfig(
                    name="NSE:NIFTY50-INDEX", mode="candle", timeframe=30
                )],
                params={},
            )
        ],
    )


@pytest.mark.asyncio
async def test_engine_starts_and_stops():
    from unittest.mock import patch
    from src.broker.registry import BrokerRegistry

    config = make_test_config()
    engine = Engine(config)

    # Patch broker registry to return mocks
    with patch.object(BrokerRegistry, "get_data_broker", return_value=MockDataBroker()), \
         patch.object(BrokerRegistry, "get_order_broker", return_value=MockOrderBroker()):
        await engine.start()
        assert engine._running is True
        assert len(engine._strategies) == 1
        assert engine._strategies[0].strategy_id == "STRATEGY_ONE"
        await engine.stop()
        assert engine._running is False


@pytest.mark.asyncio
async def test_engine_loads_disabled_strategy():
    from unittest.mock import patch
    from src.broker.registry import BrokerRegistry

    config = make_test_config()
    config.strategies[0].enabled = False
    engine = Engine(config)

    with patch.object(BrokerRegistry, "get_data_broker", return_value=MockDataBroker()), \
         patch.object(BrokerRegistry, "get_order_broker", return_value=MockOrderBroker()):
        await engine.start()
        assert len(engine._strategies) == 0  # disabled = not loaded
        await engine.stop()