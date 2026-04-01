from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..data_model import Candle, Tick


class ICandleBuilder(ABC):

    @abstractmethod
    def update(self, tick: Tick) -> Optional[Candle]:
        """
        Feed a tick. Returns a *closed* Candle if the current bar just completed,
        None otherwise.
        """

    @abstractmethod
    def get_current(self) -> Optional[Candle]:
        """Return the live (not yet closed) candle, or None if no data yet."""

    @abstractmethod
    def reset(self) -> None:
        """Discard current bar state (use on reconnect or gap detection)."""