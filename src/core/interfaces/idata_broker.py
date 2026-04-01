from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, List

from ..data_model import Candle, Tick


class IDataBroker(ABC):

    @abstractmethod
    async def connect(self) -> None:
        """Establish websocket / session."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close connection."""

    @abstractmethod
    async def subscribe(
        self,
        symbols: List[str],
        on_tick: Callable[[Tick], None],
    ) -> None:
        """Subscribe to live tick feed for given symbols."""

    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> None:
        """Remove live subscription."""

    @abstractmethod
    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: int,
        from_dt: datetime,
        to_dt: datetime,
    ) -> List[Candle]:
        """Fetch historical OHLCV candles."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return live connection state."""