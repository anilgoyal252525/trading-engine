from utils.logger import logger
from utils.error_handling import error_handling
from data_model.data_model import TradeData

@error_handling
class TrailingManager:
    async def start_trailing_sl(fyers_order_placement, trade_data: TradeData, tick: dict):
        if not trade_data or not tick:
            return

        tick_ltp = tick.get("ltp")
        if tick_ltp is None:
            return

        stop_order_id = trade_data.stop_order_id
        if not stop_order_id:
            return

        trailing_levels = trade_data.trailing_levels or []
        trailing_history = trade_data.trailing_history or []

        for level in trailing_levels:
            if any(hist.get("level") == level.get("msg") for hist in trailing_history):
                continue

            if tick_ltp > level.get("threshold", float("inf")):
                try:
                    res = await fyers_order_placement.modify_order(
                        stop_order_id,
                        order_type=4,
                        limit_price=level.get("new_stop"),
                        stop_price=level.get("new_stop"),
                        qty=trade_data.qty or 1,
                    )
                except Exception as e:
                    logger.error(f"[{trade_data.strategy_id}] Trailing SL Error {trade_data.symbol} | {level.get('msg')} | {e}")
                    continue

                if res.get('code') == 1102:
                    # Update trade trailing history
                    trade_data.trailing_history.append({
                        "ltp": tick_ltp,
                        "level": level.get("msg"),
                        "stop_price": level.get("new_stop")
                    })
                    logger.info(f"[{trade_data.strategy_id}] Trailing SL updated {trade_data.symbol} | {level.get('msg')} LTP: {tick_ltp}")
                    break
                else:
                    logger.warning(f"[{trade_data.strategy_id}] Trailing SL failed {trade_data.symbol} | {level.get('msg')} Response: {res}")
