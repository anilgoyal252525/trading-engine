import asyncio
from websocket_manager.data_manager.base import BaseWSManager
from websocket_manager.data_manager.fyers_data_websocket import FyersBroker
from websocket_manager.position_manager.fyers_position_webscoket import FyersOrderManager
from strategies.strategy_one.strategy_one import StrategyOne
from utils.logger import logger
from utils.error_handling import error_handling
import os

@error_handling
async def main():
    logger.info("ALGO STARTED")
    
    loop = asyncio.get_running_loop()
    
    # Initialize both brokers using same interface
    data_broker = FyersBroker()
    order_broker = FyersOrderManager()
    
    # Initialize manager with both websockets
    ws_mgr = BaseWSManager(data_broker=data_broker, order_broker=order_broker)
    
    # Start all connections
    await ws_mgr.start()
    
    # Subscribe symbols
    ws_mgr.subscribe_symbol("NSE:NIFTY50-INDEX", mode="candle", timeframe=30)
    logger.info("ALL RESOURCES SUBSCRIBED")
    
    # Run strategy
    strategy = StrategyOne("strategy_one", ws_mgr, loop, max_trades=1)
    await strategy.run()
    
    # Stop all connections
    await ws_mgr.stop()
    
    logger.info("[Main] Program terminated")
    await logger.flush()
    os._exit(0)

if __name__ == "__main__":
    asyncio.run(main())
