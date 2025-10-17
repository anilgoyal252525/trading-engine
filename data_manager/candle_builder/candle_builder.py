import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
from data_model.data_model import Tick, Candle

class CandleBuilder:
    __slots__ = ('event_bus', 'tick_data', 'tick_count', 'last_tick_time', 
                 'active', 'last_close', 'completion_tasks', 'max_ticks')

    def __init__(self, event_bus, max_ticks: int = 1000):
        self.event_bus = event_bus
        self.tick_data: Dict[str, np.ndarray] = {}
        self.tick_count: Dict[str, int] = {}
        self.last_tick_time: Dict[str, float] = {}
        self.active: Dict[str, tuple] = {}  # (start_time, open, high, low, close, volume)
        self.last_close: Dict[str, float] = {}
        self.completion_tasks: Dict[str, asyncio.Task] = {}
        self.max_ticks = max_ticks

    def _align_to_candle_boundary(self, dt: datetime, tf: int) -> Optional[datetime]:
        session_start = dt.replace(hour=9, minute=15, second=0, microsecond=0)
        if dt < session_start:
            return None
        secs = (dt - session_start).total_seconds()
        return session_start + timedelta(seconds=int(secs // tf) * tf)

    def _ensure_buffer(self, symbol: str) -> None:
        if symbol not in self.tick_data:
            self.tick_data[symbol] = np.zeros((self.max_ticks, 3), dtype=np.float64)
            self.tick_count[symbol] = 0

    async def process_candle_tick(self, tick: Tick, tf: int) -> None:
        if not tick or tick.ltp is None or tick.timestamp is None:
            return

        symbol = tick.symbol
        self._ensure_buffer(symbol)

        idx = self.tick_count[symbol] % self.max_ticks
        self.tick_data[symbol][idx] = [tick.timestamp, tick.ltp, tick.volume or 0]
        self.tick_count[symbol] += 1
        self.last_tick_time[symbol] = tick.timestamp

        now = datetime.now()
        start = self._align_to_candle_boundary(now, tf)
        if not start:
            return

        start_ts = start.timestamp()

        if symbol not in self.active or self.active[symbol][0] != start_ts:
            if symbol in self.active:
                await self._complete_candle(symbol, tf)

            self.active[symbol] = (start_ts, tick.ltp, tick.ltp, tick.ltp, tick.ltp, tick.volume or 0)

            delay = (start + timedelta(seconds=tf) - now).total_seconds()
            if delay > 0:
                if task := self.completion_tasks.get(symbol):
                    task.cancel()
                self.completion_tasks[symbol] = asyncio.create_task(
                    self._scheduled_complete(symbol, tf, delay)
                )
        else:
            start_ts, o, h, l, c, v = self.active[symbol]
            self.active[symbol] = (
                start_ts, o,
                max(h, tick.ltp),
                min(l, tick.ltp),
                tick.ltp,
                v + (tick.volume or 0)
            )

    async def _scheduled_complete(self, symbol: str, tf: int, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            if symbol in self.active:
                await self._complete_candle(symbol, tf)
                self.active.pop(symbol, None)
        except asyncio.CancelledError:
            pass

    async def _complete_candle(self, symbol: str, tf: int) -> None:
        if symbol not in self.active:
            return

        start_ts, o, h, l, c, v = self.active[symbol]
        start = datetime.fromtimestamp(start_ts)
        end_ts = start_ts + tf

        count = self.tick_count[symbol]
        if count == 0:
            return

        n = min(count, self.max_ticks)
        data = self.tick_data[symbol][:n] if count <= self.max_ticks else \
               np.roll(self.tick_data[symbol], -count % self.max_ticks, axis=0)

        mask = (data[:, 0] >= start_ts) & (data[:, 0] < end_ts)
        valid_ticks = data[mask]

        if len(valid_ticks) > 0:
            prices = valid_ticks[:, 1]
            o = prices[0]
            h = np.max(prices)
            l = np.min(prices)
            c = prices[-1]
            v = np.sum(valid_ticks[:, 2])
        elif (last := self.last_close.get(symbol)) is not None:
            o = h = l = c = last

        self.last_close[symbol] = c

        candle = Candle(
            symbol=symbol,
            open=float(o),
            high=float(h),
            low=float(l),
            close=float(c),
            start_time=start,
            volume=int(v)
        )
        await self.event_bus.publish("candle", candle)

    def cleanup_inactive_symbols(self, current_time: float, ttl: int = 3600) -> int:
        cutoff = current_time - ttl
        inactive = [s for s, ts in self.last_tick_time.items() if ts < cutoff]
        for symbol in inactive:
            self.tick_data.pop(symbol, None)
            self.tick_count.pop(symbol, None)
            self.last_tick_time.pop(symbol, None)
            self.active.pop(symbol, None)
            if task := self.completion_tasks.pop(symbol, None):
                task.cancel()
        return len(inactive)
