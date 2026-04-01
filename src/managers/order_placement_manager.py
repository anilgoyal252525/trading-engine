from __future__ import annotations

import logging
from datetime import datetime

from ..core.data_model import Signal, TradeData
from ..core.enums import TradeStatus
from ..core.interfaces.iorder_broker import IOrderBroker
from .trade_state_manager import TradeStateManager

logger = logging.getLogger(__name__)


class OrderPlacementManager:
    """
    Broker-agnostic order placement.
    Coordinates between a Signal, IOrderBroker, and TradeStateManager.
    Strategies call this — they never touch the broker directly.
    """

    def __init__(
        self,
        order_broker: IOrderBroker,
        trade_state_manager: TradeStateManager,
    ) -> None:
        self._broker = order_broker
        self._tsm = trade_state_manager

    async def place(self, signal: Signal, strategy_id: str) -> TradeData:
        """
        Place an order for a signal.
        Creates a TradeData record and returns it.
        Raises on broker error — caller handles retry logic.
        """
        trade = TradeData(
            trade_id="",
            strategy_id=strategy_id,
            symbol=signal.symbol,
            side=signal.side,
            quantity=signal.quantity,
            entry_price=signal.price,
            sl=signal.sl,
            target=signal.target,
            status=TradeStatus.PENDING,
            entry_time=datetime.now(),
            tag=signal.tag,
        )
        trade = self._tsm.create_trade(trade)

        try:
            order_id = await self._broker.place_order(signal)
            trade.order_id = order_id
            trade.status = TradeStatus.OPEN
            self._tsm.update_status(trade.trade_id, TradeStatus.OPEN)
            logger.info("Order placed: %s | order_id=%s", trade.trade_id, order_id)
        except Exception as exc:
            trade.status = TradeStatus.FAILED
            self._tsm.update_status(trade.trade_id, TradeStatus.FAILED)
            logger.error("Order failed: %s | %s", trade.trade_id, exc)
            raise

        return trade

    async def exit_trade(self, trade_id: str, exit_signal: Signal) -> TradeData:
        """
        Place an exit order and close the trade record.
        """
        order_id = await self._broker.place_order(exit_signal)
        trade = self._tsm.close_trade(trade_id, exit_signal.price)
        logger.info("Exit order placed: %s | order_id=%s", trade_id, order_id)
        return trade