from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from ..core.data_model import Candle, Tick
from ..core.interfaces.icandle_builder import ICandleBuilder

logger = logging.getLogger(__name__)

# Key: (symbol, timeframe_minutes)
_BuilderKey = Tuple[str, int]


class TimeframeCandleBuilder(ICandleBuilder):
    """Builds OHLCV candles from ticks for a fixed timeframe."""

    def __init__(self, symbol: str, timeframe: int) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self._current: Optional[Candle] = None
        self._bar_open_time: Optional[datetime] = None

    def update(self, tick: Tick) -> Optional[Candle]:
        """
        Feed a tick. Returns closed Candle if bar just ended, else None.
        """
        bar_time = self._get_bar_open(tick.timestamp)

        if self._current is None or bar_time > self._bar_open_time:
            # New bar started
            closed = None
            if self._current is not None:
                self._current.is_closed = True
                closed = self._current

            self._bar_open_time = bar_time
            self._current = Candle(
                symbol=self.symbol,
                timeframe=self.timeframe,
                open=tick.ltp,
                high=tick.ltp,
                low=tick.ltp,
                close=tick.ltp,
                volume=tick.volume,
                timestamp=bar_time,
                is_closed=False,
            )
            return closed
        else:
            # Update existing bar
            self._current.high = max(self._current.high, tick.ltp)
            self._current.low = min(self._current.low, tick.ltp)
            self._current.close = tick.ltp
            self._current.volume += tick.volume
            return None

    def get_current(self) -> Optional[Candle]:
        return self._current

    def reset(self) -> None:
        self._current = None
        self._bar_open_time = None

    def _get_bar_open(self, ts: datetime) -> datetime:
        """Truncate timestamp to nearest timeframe boundary."""
        minutes = ts.hour * 60 + ts.minute
        bar_start_minutes = (minutes // self.timeframe) * self.timeframe
        return ts.replace(
            hour=bar_start_minutes // 60,
            minute=bar_start_minutes % 60,
            second=0,
            microsecond=0,
        )


class CandleManager:
    """
    Manages per-symbol, per-timeframe candle builders.
    Strategies register their (symbol, timeframe) pairs.
    On each tick, CandleManager updates the right builder and
    calls registered listeners when a candle closes.
    """

    def __init__(self) -> None:
        self._builders: Dict[_BuilderKey, TimeframeCandleBuilder] = {}
        self._listeners: Dict[_BuilderKey, List[Callable[[Candle], None]]] = {}

    def register(
        self,
        symbol: str,
        timeframe: int,
        on_candle: Callable[[Candle], None],
    ) -> None:
        """Register a closed-candle callback for (symbol, timeframe)."""
        key = (symbol, timeframe)
        if key not in self._builders:
            self._builders[key] = TimeframeCandleBuilder(symbol, timeframe)
            self._listeners[key] = []
        self._listeners[key].append(on_candle)

    def on_tick(self, tick: Tick) -> None:
        """
        Called by SymbolManager for every tick.
        Update all builders watching this symbol.
        """
        for (sym, tf), builder in self._builders.items():
            if sym != tick.symbol:
                continue
            closed = builder.update(tick)
            if closed is not None:
                for cb in self._listeners.get((sym, tf), []):
                    try:
                        cb(closed)
                    except Exception:
                        logger.exception(
                            "Candle listener error for %s tf=%d", sym, tf
                        )

    def get_current(self, symbol: str, timeframe: int) -> Optional[Candle]:
        return self._builders.get((symbol, timeframe), None) and \
               self._builders[(symbol, timeframe)].get_current()