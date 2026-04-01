from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ..core.data_model import Candle, Signal, Tick
from ..core.interfaces.istrategy import IStrategy
from ..infrastructure.config_loader import StrategyConfig
from ..managers.candle_manager import CandleManager
from ..managers.order_placement_manager import OrderPlacementManager
from ..managers.trade_state_manager import TradeStateManager

logger = logging.getLogger(__name__)


class BaseStrategy(IStrategy):
    """
    Template Method pattern.
    Subclasses implement: `entry_signal`, `exit_signal` (optional: `on_tick`).
    BaseStrategy handles: max_trades guard, queue processing, lifecycle.
    """

    def __init__(self, config: StrategyConfig) -> None:
        self._config = config
        self._opm: Optional[OrderPlacementManager] = None
        self._tsm: Optional[TradeStateManager] = None
        self._candle_manager: Optional[CandleManager] = None
        self._running = False

    # ------------------------------------------------------------------ #
    #  IStrategy — lifecycle
    # ------------------------------------------------------------------ #

    @property
    def strategy_id(self) -> str:
        return self._config.id

    async def start(self) -> None:
        self._running = True
        logger.info("Strategy started: %s", self.strategy_id)

    async def stop(self) -> None:
        self._running = False
        logger.info("Strategy stopped: %s", self.strategy_id)

    # ------------------------------------------------------------------ #
    #  IStrategy — data callbacks
    # ------------------------------------------------------------------ #

    async def on_candle(self, candle: Candle) -> None:
        if not self._running:
            return

        open_trades = self._tsm.get_open_trades(self.strategy_id)

        # Check exit on open trades first
        for trade in open_trades:
            if trade.symbol == candle.symbol:
                exit_sig = self.exit_signal(candle, trade)
                if exit_sig and self._opm:
                    await self._opm.exit_trade(trade.trade_id, exit_sig)
                    return

        # Check entry if under max_trades
        if self._tsm.open_trade_count(self.strategy_id) < self._config.max_trades:
            entry_sig = self.entry_signal(candle)
            if entry_sig and self._opm:
                await self._opm.place(entry_sig, self.strategy_id)

    async def on_tick(self, tick: Tick) -> None:
        """Override in subclass for tick-mode strategies."""
        pass

    # ------------------------------------------------------------------ #
    #  Template methods — subclasses MUST implement entry_signal
    # ------------------------------------------------------------------ #

    def entry_signal(self, candle: Candle) -> Optional[Signal]:
        """Return a Signal to enter, or None to skip."""
        raise NotImplementedError

    def exit_signal(self, candle: Candle, trade) -> Optional[Signal]:
        """Return a Signal to exit, or None to hold."""
        return None

    # ------------------------------------------------------------------ #
    #  Wiring — called by engine before start()
    # ------------------------------------------------------------------ #

    def wire(
        self,
        opm: OrderPlacementManager,
        tsm: TradeStateManager,
        candle_manager: CandleManager,
    ) -> None:
        self._opm = opm
        self._tsm = tsm
        self._candle_manager = candle_manager