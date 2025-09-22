# csv_builder.py
import aiofiles
import aiofiles.os
import os
import json
from datetime import datetime
from utils.error_handling import error_handling
import asyncio
import csv
from io import StringIO

@error_handling
class CSVBuilder:
    def __init__(self, base_dir: str = None, prefix: str = "trades"):
        self.base_dir = base_dir or os.path.join(os.getcwd(), "logger_files", "csv")
        os.makedirs(self.base_dir, exist_ok=True)

        self.prefix = prefix
        self.file_path = ""
        self.header_written = False
        self._lock = asyncio.Lock()  # ensure async safety

    @staticmethod
    async def _format_time(dt_value: datetime = None) -> str:
        dt_value = dt_value or datetime.now()
        if isinstance(dt_value, datetime):
            return dt_value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return str(dt_value)

    async def log_trade(self, trade_no: int, order_id: str, details: dict):
        # Rotate file daily
        today_file = os.path.join(
            self.base_dir, f"{self.prefix}_{datetime.now().strftime('%Y-%m-%d')}.csv"
        )
        if self.file_path != today_file:
            self.file_path = today_file
            self.header_written = False

        # Extract fields
        entry = details.get("entry_price")
        stop = details.get("initial_stop_price")
        target = details.get("target_price")
        qty = details.get("qty", 1)
        position_id = details.get("position_id", 1)

        side = details.get("side")
        if side is None:
            side = "BUY" if entry and target and target > entry else "SELL"

        trade_row = {
            "trade_no": trade_no,
            "order_id": order_id,
            "symbol": details.get("symbol"),
            "position_id": position_id,
            "qty": qty,
            "side": side,
            "entry_price": entry,
            "initial_stop_price": stop,
            "target_price": target,
            "initial_sl_points": (stop - entry) if entry and stop else None,
            "target_points": (target - entry) if entry and target else None,
            "order_exit_time": await self._format_time(),
            "trailing_levels": json.dumps(details.get("trailing_levels", [])),
            "trailing_history": json.dumps(details.get("trailing_history", [])),
            "timestamp": await self._format_time(),
        }

        # Ensure async-safe writes
        async with self._lock:
            file_exists = await aiofiles.os.path.exists(self.file_path)
            async with aiofiles.open(self.file_path, mode="a", newline="", encoding="utf-8") as f:
                # Write header if new file
                if not file_exists or not self.header_written:
                    output = StringIO()
                    writer = csv.DictWriter(output, fieldnames=trade_row.keys())
                    writer.writeheader()
                    await f.write(output.getvalue())
                    self.header_written = True

                # Write row safely
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=trade_row.keys())
                writer.writerow(trade_row)
                await f.write(output.getvalue())

# Instantiate singleton
csv_builder = CSVBuilder()