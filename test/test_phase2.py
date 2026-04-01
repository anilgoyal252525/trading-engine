"""
Run: pytest tests/test_phase2.py -v
"""
import pytest
import asyncio

from src.broker.registry import BrokerRegistry
import src.broker  # noqa — triggers registration


def test_registry_data_broker_resolves():
    broker = BrokerRegistry.get_data_broker("fyers")
    assert broker is not None
    assert not broker.is_connected


def test_registry_order_broker_resolves():
    broker = BrokerRegistry.get_order_broker("fyers")
    assert broker is not None


def test_registry_unknown_broker_raises():
    with pytest.raises(ValueError, match="not registered"):
        BrokerRegistry.get_data_broker("zerodha_not_registered_yet")


def test_case_insensitive_lookup():
    b1 = BrokerRegistry.get_data_broker("Fyers")
    b2 = BrokerRegistry.get_data_broker("FYERS")
    assert type(b1) == type(b2)


@pytest.mark.asyncio
async def test_connect_disconnect():
    broker = BrokerRegistry.get_data_broker("fyers")
    await broker.connect()
    assert broker.is_connected
    await broker.disconnect()
    assert not broker.is_connected


@pytest.mark.asyncio
async def test_place_order_returns_id():
    from src.core.data_model import Signal
    from src.core.enums import OrderSide, OrderType

    broker = BrokerRegistry.get_order_broker("fyers")
    sig = Signal(
        symbol="NSE:NIFTY50-INDEX",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=50,
    )
    order_id = await broker.place_order(sig)
    assert isinstance(order_id, str)
    assert len(order_id) > 0