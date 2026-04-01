from __future__ import annotations

from typing import Dict, List, Optional

from ...core.data_model import Candle, Signal, TradeData
from ...infrastructure.config_loader import StrategyConfig
from ..base_strategy import BaseStrategy
from .config import StrategyOneParams
from .logic import compute_entry, compute_exit


class Handler(BaseStrategy):
    """
    Wires StrategyOne logic to the BaseStrategy template.
    Only touches entry/exit conditions — all orchestration is in BaseStrategy.
    """

    def __init__(self, config: StrategyConfig) -> None:
        super().__init__(config)
        self._params = StrategyOneParams.from_dict(config.params)
        # Per-symbol candle history (last N candles for indicators)
        self._history: Dict[str, List[Candle]] = {}
        self._MAX_HISTORY = 50

    def entry_signal(self, candle: Candle) -> Optional[Signal]:
        history = self._history.get(candle.symbol, [])
        signal = compute_entry(candle, history, self._params)
        # Append to history after computing (candle is now the latest)
        history.append(candle)
        if len(history) > self._MAX_HISTORY:
            history.pop(0)
        self._history[candle.symbol] = history
        return signal

    def exit_signal(self, candle: Candle, trade: TradeData) -> Optional[Signal]:
        return compute_exit(candle, trade, self._params)