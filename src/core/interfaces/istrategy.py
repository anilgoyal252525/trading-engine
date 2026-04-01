from __future__ import annotations

from abc import ABC, abstractmethod

from ..data_model import Candle, Tick


class IStrategy(ABC):

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique strategy identifier from config."""

    @abstractmethod
    async def on_candle(self, candle: Candle) -> None:
        """Called when a closed candle arrives for any subscribed symbol."""

    @abstractmethod
    async def on_tick(self, tick: Tick) -> None:
        """Called on every tick for tick-mode symbols."""

    @abstractmethod
    async def start(self) -> None:
        """Called once before market data starts flowing."""

    @abstractmethod
    async def stop(self) -> None:
        """Called during graceful shutdown — flush state, cancel pending orders."""