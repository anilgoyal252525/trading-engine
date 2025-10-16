import aiofiles
import aiofiles.os
import os
import asyncio
import csv
from io import StringIO
from datetime import datetime
from common_utils.error_handling import error_handling
from data_model.data_model import TradeData
from dataclasses import asdict

@error_handling
class CSVBuilder:
    def __init__(self, event_bus, base_dir: str = None, prefix: str = "trades"):
        self.event_bus = event_bus
        self.base_dir = base_dir or os.path.join(os.getcwd(), "logger_files", "csv")
        os.makedirs(self.base_dir, exist_ok=True)
        self.prefix = prefix
        self.file_path = ""
        self._lock = asyncio.Lock()
        self._queue = None
        self._consumer_task = None
        self._running = False

        # Start the background task
        self._consumer_task = asyncio.create_task(self._start_consumer())

    async def _start_consumer(self):
        self._queue = self.event_bus.subscribe("trade_close")
        self._running = True
        
        try:
            while self._running:
                try:
                    # Use wait_for with timeout to allow periodic checking of _running flag
                    trade: TradeData = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    await self._log_trade(trade)
                except asyncio.TimeoutError:
                    continue  # No trade received, loop continues to check _running flag
        except asyncio.CancelledError:
            pass  # Task cancelled, exit gracefully
        finally:
            self._running = False


    async def _log_trade(self, trade: TradeData):
        today_file = os.path.join(
            self.base_dir, f"{self.prefix}_{datetime.now().strftime('%Y-%m-%d')}.csv"
        )

        if self.file_path != today_file:
            self.file_path = today_file
            self._file_exists = await aiofiles.os.path.exists(self.file_path)

        async with self._lock:
            async with aiofiles.open(self.file_path, mode="a", newline="", encoding="utf-8") as f:
                row_dict = asdict(trade)
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=row_dict.keys())

                if not self._file_exists:
                    writer.writeheader()
                    await f.write(output.getvalue())
                    self._file_exists = True
                    output = StringIO()
                    writer = csv.DictWriter(output, fieldnames=row_dict.keys())

                writer.writerow(row_dict)
                await f.write(output.getvalue())

    async def stop(self):
        self._running = False
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
