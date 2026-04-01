from __future__ import annotations

import asyncio
import logging
import signal
from typing import List

import uvloop

from .broker.registry import BrokerRegistry
from .infrastructure.config_loader import AppConfig, load_config
from .managers.candle_manager import CandleManager
from .managers.order_placement_manager import OrderPlacementManager
from .managers.symbol_manager import SymbolManager
from .managers.trade_state_manager import TradeStateManager
from .strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


class Engine:
    """
    Single orchestrator.
    Startup:  connect brokers → wire managers → load strategies → subscribe → run
    Shutdown: stop strategies → flush orders → disconnect brokers
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._data_broker = None
        self._order_broker = None
        self._symbol_manager: SymbolManager | None = None
        self._candle_manager: CandleManager | None = None
        self._trade_state_manager: TradeStateManager | None = None
        self._order_placement_manager: OrderPlacementManager | None = None
        self._strategies = []
        self._running = False

    # ------------------------------------------------------------------ #
    #  Startup
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        logger.info("=== Engine starting ===")

        # 1. Brokers
        self._data_broker = BrokerRegistry.get_data_broker(self._config.brokers.data)
        self._order_broker = BrokerRegistry.get_order_broker(self._config.brokers.order)
        await self._data_broker.connect()
        await self._order_broker.connect()
        logger.info("Brokers connected: data=%s order=%s",
                    self._config.brokers.data, self._config.brokers.order)

        # 2. Managers
        self._candle_manager = CandleManager()
        self._trade_state_manager = TradeStateManager()
        self._symbol_manager = SymbolManager(self._data_broker)
        self._order_placement_manager = OrderPlacementManager(
            self._order_broker, self._trade_state_manager
        )

        # 3. Load strategies
        self._strategies = StrategyRegistry.load(self._config.strategies)
        for strat in self._strategies:
            strat.wire(
                self._order_placement_manager,
                self._trade_state_manager,
                self._candle_manager,
            )

        # 4. Subscribe symbols
        for strat_cfg in self._config.strategies:
            if not strat_cfg.enabled:
                continue
            for sym_cfg in strat_cfg.symbols:
                if sym_cfg.mode == "candle":
                    self._candle_manager.register(
                        sym_cfg.name,
                        sym_cfg.timeframe,
                        self._make_candle_dispatcher(sym_cfg.name, sym_cfg.timeframe),
                    )
                await self._symbol_manager.subscribe(
                    sym_cfg.name,
                    self._candle_manager.on_tick,
                )

        # 5. Start strategies
        await asyncio.gather(*[s.start() for s in self._strategies])

        self._running = True
        logger.info("=== Engine running | strategies=%d ===", len(self._strategies))

    # ------------------------------------------------------------------ #
    #  Shutdown (reverse order, graceful)
    # ------------------------------------------------------------------ #

    async def stop(self) -> None:
        logger.info("=== Engine shutting down ===")
        self._running = False

        # 1. Stop strategies
        if self._strategies:
            await asyncio.gather(*[s.stop() for s in self._strategies])

        # 2. Disconnect brokers
        if self._data_broker:
            await self._data_broker.disconnect()
        if self._order_broker:
            await self._order_broker.disconnect()

        logger.info("=== Engine stopped ===")

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _make_candle_dispatcher(self, symbol: str, timeframe: int):
        """
        Returns a closed-candle callback that fans out to all strategies
        watching this (symbol, timeframe).
        """
        strategies = self._strategies

        async def _dispatch(candle):
            tasks = []
            for strat in strategies:
                cfg = next(
                    (s for s in self._config.strategies if s.id == strat.strategy_id),
                    None
                )
                if cfg is None:
                    continue
                for sym in cfg.symbols:
                    if sym.name == symbol and sym.timeframe == timeframe:
                        tasks.append(strat.on_candle(candle))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        def _sync_wrapper(candle):
            asyncio.get_event_loop().create_task(_dispatch(candle))

        return _sync_wrapper

    async def run_forever(self) -> None:
        """Block until SIGINT / SIGTERM."""
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def _signal_handler():
            logger.info("Shutdown signal received")
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

        await stop_event.wait()
        await self.stop()