import asyncio
from strategies.strategy_one.strategy_one import StrategyOne
from common_utils.logger import logger

class StrategyManager:
    def __init__(self, resource_manager):
        self.resource_manager = resource_manager
        self.loop = asyncio.get_running_loop()
        self.strategies = []

    def register_strategies(self):
        strategy_one = StrategyOne(
            self.resource_manager.event_bus,
            "strategy_one",
            self.resource_manager.ws_mgr,
            self.loop,
            max_trades=1
        )
        self.strategies.append(strategy_one)
        logger.info("[StrategyManager] Registered StrategyOne")

    async def run_all(self):
        logger.info("[StrategyManager] Running all strategies...")
        await asyncio.gather(*(strategy.run() for strategy in self.strategies))
