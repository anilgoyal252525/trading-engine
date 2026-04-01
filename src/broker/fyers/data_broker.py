from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable, Dict, List, Optional

from ...core.data_model import Candle, Tick
from ...core.interfaces.idata_broker import IDataBroker
from ..registry import register_data_broker


@register_data_broker("fyers")
class FyersDataBroker(IDataBroker):
    """
    Adapter: wraps your existing Fyers websocket code behind IDataBroker.
    Replace the _fyers_* stubs with your real Fyers SDK calls.
    """

    def __init__(self, access_token: Optional[str] = None, **kwargs):
        self._access_token = access_token
        self._connected = False
        self._subscriptions: Dict[str, Callable[[Tick], None]] = {}
        # TODO: store your real Fyers SDK client here
        # self._ws = FyersDataSocket(access_token=access_token, ...)

    # ------------------------------------------------------------------ #
    #  IDataBroker implementation
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        """
        Replace with your real Fyers websocket connect.
        Keep the _connected flag update.
        """
        # await self._ws.connect()
        self._connected = True

    async def disconnect(self) -> None:
        # await self._ws.close()
        self._connected = False

    async def subscribe(
        self,
        symbols: List[str],
        on_tick: Callable[[Tick], None],
    ) -> None:
        for symbol in symbols:
            self._subscriptions[symbol] = on_tick
        # TODO: call your real Fyers subscribe
        # self._ws.subscribe(symbols=symbols, data_type="symbolData")

    async def unsubscribe(self, symbols: List[str]) -> None:
        for symbol in symbols:
            self._subscriptions.pop(symbol, None)
        # self._ws.unsubscribe(symbols=symbols)

    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: int,
        from_dt: datetime,
        to_dt: datetime,
    ) -> List[Candle]:
        """
        Replace with your real Fyers history API call.
        Map the raw response to List[Candle].
        """
        # Example skeleton — replace body:
        # raw = self._fyers.history(symbol=symbol, resolution=str(timeframe), ...)
        # return [self._map_candle(r, symbol, timeframe) for r in raw["candles"]]
        return []

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _on_tick_raw(self, raw: dict) -> None:
        """
        Fyers websocket message callback.
        Parse raw dict → Tick → call subscriber.
        Plug your existing parsing logic here.
        """
        symbol = raw.get("symbol", "")
        if symbol not in self._subscriptions:
            return
        tick = Tick(
            symbol=symbol,
            ltp=float(raw.get("ltp", 0)),
            timestamp=datetime.fromtimestamp(raw.get("timestamp", 0)),
            volume=int(raw.get("vol_traded_today", 0)),
            bid=float(raw.get("bid_price", 0)),
            ask=float(raw.get("ask_price", 0)),
        )
        callback = self._subscriptions[symbol]
        asyncio.get_event_loop().call_soon_threadsafe(
            asyncio.ensure_future, asyncio.coroutine(lambda: callback(tick))()
        )

    @staticmethod
    def _map_candle(row: list, symbol: str, timeframe: int) -> Candle:
        """Map a raw Fyers candle row [epoch, o, h, l, c, vol] to Candle."""
        ts, o, h, l, c, vol = row
        return Candle(
            symbol=symbol,
            timeframe=timeframe,
            open=o, high=h, low=l, close=c,
            volume=int(vol),
            timestamp=datetime.fromtimestamp(ts),
            is_closed=True,
        )