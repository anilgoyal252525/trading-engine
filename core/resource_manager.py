import asyncio
from broker.fyers_broker.fyers_data_websocket import FyersDataBroker
from broker.fyers_broker.fyers_position_webscoket import FyersOrderPositionTracker
from data_manager.data_manager import DataManager
from data_manager.candle_builder.candle_builder import CandleBuilder
from common_utils.csv_builder import CSVBuilder
from central_hub.event_bus import EventBus
from common_utils.logger import logger

class ResourceManager:
    def __init__(self):
        self.event_bus = EventBus()
        self.data_socket = FyersDataBroker()
        self.position_order_socket = FyersOrderPositionTracker()
        self.csv_builder = CSVBuilder(self.event_bus)
        self.candle_builder = CandleBuilder(event_bus=self.event_bus)
        self.ws_mgr = DataManager(
            event_bus=self.event_bus,
            data_broker=self.data_socket,
            order_broker=self.position_order_socket,
            candle_builder=self.candle_builder
        )

    async def start(self):
        await logger.start()
        logger.info("[ResourceManager] Starting resources...")
        await self.ws_mgr.start()
        logger.info("[ResourceManager] Resources started successfully.")

    def subscribe_symbols(self):
        logger.info("[ResourceManager] Subscribing symbols...")
        self.ws_mgr.subscribe_symbol("NSE:NIFTY50-INDEX", mode="candle", timeframe=30)
        logger.info("[ResourceManager] Symbol subscription done.")

    async def stop(self):
        logger.info("[ResourceManager] Stopping all resources...")
        await self.ws_mgr.stop()
        await self.csv_builder.stop()
        await logger.stop()
        logger.info("[ResourceManager] All resources stopped.")
