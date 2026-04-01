from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Dict, List, Optional

from ..core.data_model import TradeData
from ..core.enums import TradeStatus

logger = logging.getLogger(__name__)


class TradeStateManager:
    """
    Global in-memory store for all trades across all strategies.
    Single source of truth for open position counts.
    """

    def __init__(self) -> None:
        # trade_id → TradeData
        self._trades: Dict[str, TradeData] = {}

    # ------------------------------------------------------------------ #
    #  Write operations
    # ------------------------------------------------------------------ #

    def create_trade(self, trade: TradeData) -> TradeData:
        if not trade.trade_id:
            trade.trade_id = str(uuid.uuid4())
        self._trades[trade.trade_id] = trade
        logger.info("Trade created: %s | %s %s", trade.trade_id, trade.side.value, trade.symbol)
        return trade

    def update_status(self, trade_id: str, status: TradeStatus) -> None:
        if trade_id not in self._trades:
            raise KeyError(f"Trade not found: {trade_id}")
        self._trades[trade_id].status = status
        logger.info("Trade %s → %s", trade_id, status.value)

    def close_trade(self, trade_id: str, exit_price: float) -> TradeData:
        trade = self._get_or_raise(trade_id)
        trade.exit_price = exit_price
        trade.status = TradeStatus.CLOSED
        trade.compute_pnl()
        logger.info("Trade closed: %s | PnL: %.2f", trade_id, trade.pnl)
        return trade

    # ------------------------------------------------------------------ #
    #  Read operations
    # ------------------------------------------------------------------ #

    def get_trade(self, trade_id: str) -> Optional[TradeData]:
        return self._trades.get(trade_id)

    def get_open_trades(self, strategy_id: Optional[str] = None) -> List[TradeData]:
        open_statuses = {TradeStatus.OPEN, TradeStatus.PENDING}
        trades = [t for t in self._trades.values() if t.status in open_statuses]
        if strategy_id:
            trades = [t for t in trades if t.strategy_id == strategy_id]
        return trades

    def open_trade_count(self, strategy_id: str) -> int:
        return len(self.get_open_trades(strategy_id))

    def all_trades(self, strategy_id: Optional[str] = None) -> List[TradeData]:
        if strategy_id:
            return [t for t in self._trades.values() if t.strategy_id == strategy_id]
        return list(self._trades.values())

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _get_or_raise(self, trade_id: str) -> TradeData:
        if trade_id not in self._trades:
            raise KeyError(f"Trade not found: {trade_id}")
        return self._trades[trade_id]