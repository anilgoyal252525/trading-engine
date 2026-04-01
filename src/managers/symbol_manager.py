from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Set

from ..core.data_model import Tick
from ..core.interfaces.idata_broker import IDataBroker

logger = logging.getLogger(__name__)


class SymbolManager:
    """
    Manages live symbol subscriptions with reference counting.
    Multiple strategies can subscribe to the same symbol — only one
    broker subscription is created. Unsubscribe only happens when
    refcount drops to zero.
    """

    def __init__(self, data_broker: IDataBroker) -> None:
        self._broker = data_broker
        self._refcount: Dict[str, int] = defaultdict(int)
        self._subscribers: Dict[str, List[Callable[[Tick], None]]] = defaultdict(list)
        self._subscribed: Set[str] = set()

    async def subscribe(
        self,
        symbol: str,
        callback: Callable[[Tick], None],
    ) -> None:
        """
        Register a callback for `symbol`.
        Issues broker subscribe only on first registration.
        """
        self._refcount[symbol] += 1
        self._subscribers[symbol].append(callback)

        if symbol not in self._subscribed:
            await self._broker.subscribe([symbol], self._dispatch)
            self._subscribed.add(symbol)
            logger.info("Subscribed symbol: %s", symbol)

    async def unsubscribe(
        self,
        symbol: str,
        callback: Callable[[Tick], None],
    ) -> None:
        """
        Remove a callback for `symbol`.
        Issues broker unsubscribe only when all callbacks are removed.
        """
        if symbol not in self._refcount:
            return

        self._refcount[symbol] -= 1
        try:
            self._subscribers[symbol].remove(callback)
        except ValueError:
            pass

        if self._refcount[symbol] <= 0:
            del self._refcount[symbol]
            del self._subscribers[symbol]
            self._subscribed.discard(symbol)
            await self._broker.unsubscribe([symbol])
            logger.info("Unsubscribed symbol: %s", symbol)

    def _dispatch(self, tick: Tick) -> None:
        """Fan-out tick to all registered callbacks for the symbol."""
        for cb in list(self._subscribers.get(tick.symbol, [])):
            try:
                cb(tick)
            except Exception:
                logger.exception("Tick callback error for %s", tick.symbol)

    @property
    def active_symbols(self) -> List[str]:
        return list(self._subscribed)