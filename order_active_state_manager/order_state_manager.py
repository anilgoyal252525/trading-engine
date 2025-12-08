import asyncio
from typing import Dict
from common_utils.error_handling import error_handling
from data_model.data_model import TradeData

@error_handling
class ActiveTradesManager:
    def __init__(self, event_bus, strategy_id: str):
        self.event_bus = event_bus
        self.strategy_id = strategy_id
        self._trades: Dict[str, TradeData] = {}  # in-memory trades for this strategy
        self._lock = asyncio.Lock()
        self._current_active_main_order_id: str | None = None

    
    async def add_trade(self, trade_no, strategy_id, main_order_id):
        trade_data = TradeData(
            trade_no=trade_no,
            strategy_id=self.strategy_id,
            order_id=main_order_id,
        )

        async with self._lock:
            self._trades[main_order_id] = trade_data
            self._current_active_main_order_id = main_order_id

        return trade_data


    async def update_trade(self, main_order_id: str, update: Dict) -> None:
        async with self._lock:
            activeTrade = self._trades.get(main_order_id)
            if not activeTrade:
                return None 

            # professional reducer-style state patch
            for key, value in update.items():
                if hasattr(activeTrade, key):
                    setattr(activeTrade, key, value)


    async def get_active_trade(self):
        async with self._lock:
            if not self._current_active_main_order_id:
                return None
            return self._trades.get(self._current_active_main_order_id)

    
    async def close_trade(self, main_order_id: str) -> None:
        async with self._lock:
            trade = self._trades.pop(main_order_id, None)
            if trade:
                await self.event_bus.publish("trade_close", trade)
                self._current_active_main_order_id = None
