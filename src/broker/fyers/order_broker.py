from __future__ import annotations

from typing import Dict, List, Optional

from ...core.data_model import Signal, TradeData
from ...core.enums import OrderSide, OrderType, TradeStatus
from ...core.interfaces.iorder_broker import IOrderBroker
from ..registry import register_order_broker


@register_order_broker("fyers")
class FyersOrderBroker(IOrderBroker):
    """
    Adapter: wraps your existing Fyers order API behind IOrderBroker.
    """

    def __init__(self, access_token: Optional[str] = None, **kwargs):
        self._access_token = access_token
        self._connected = False
        # TODO: self._fyers = fyersModel.FyersModel(client_id=..., token=access_token)

    async def connect(self) -> None:
        # Validate token, warm up session
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def place_order(self, signal: Signal) -> str:
        """
        Map Signal → Fyers order dict, call your existing order placement.
        Returns order_id string.
        """
        order_dict = {
            "symbol": signal.symbol,
            "qty": signal.quantity,
            "type": self._map_order_type(signal.order_type),
            "side": 1 if signal.side == OrderSide.BUY else -1,
            "productType": "INTRADAY",
            "limitPrice": signal.price,
            "stopPrice": signal.sl,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
        }
        # response = self._fyers.place_order(data=order_dict)
        # return response["id"]
        return "MOCK_ORDER_ID"

    async def cancel_order(self, order_id: str) -> bool:
        # response = self._fyers.cancel_order(data={"id": order_id})
        # return response["s"] == "ok"
        return True

    async def get_order_status(self, order_id: str) -> Dict:
        # return self._fyers.order_detail(data={"id": order_id})
        return {}

    async def get_positions(self) -> List[TradeData]:
        # raw = self._fyers.positions()
        # return [self._map_position(p) for p in raw.get("netPositions", [])]
        return []

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _map_order_type(order_type: OrderType) -> int:
        return {
            OrderType.MARKET: 2,
            OrderType.LIMIT: 1,
            OrderType.SL: 4,
            OrderType.SL_M: 3,
        }[order_type]