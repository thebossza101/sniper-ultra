"""
SNIPER ULTRA — Entry Execution (4-Gate + MT5 Order Placement)
"""
import time
import MetaTrader5 as mt5
from config import SYMBOL, MAGIC, LOT_MIN, LOT_STEP
from engine.data import get_symbol_info, get_open_positions, check_mt5_health, calc_atr, get_filling_mode
from trading.risk import calc_position_size, calc_sl_tp, check_daily_limits
from utils.logger import log
from engine.confluence import calculate_full_confluence


def execute_trade(confluence, data_dict, daily_state):
    """
    Execute trade if confluence says ENTRY
    
    Returns: {'executed': bool, 'ticket': int, 'error': '', 'price': 0}
    """
    result = {'executed': False, 'ticket': 0, 'error': '', 'price': 0}

    # Check recommendation
    if confluence.get('recommendation') != 'ENTRY':
        result['error'] = f"Recommendation: {confluence.get('recommendation', 'WAIT')}"
        return result

    # Check daily limits
    limits = check_daily_limits(
        daily_state['daily_pnl'],
        daily_state['daily_losses'],
        daily_state['consecutive_losses'],
    )
    if not limits['can_trade']:
        result['error'] = limits['reason']
        return result

    direction = confluence['direction']
    if direction == 'NEUTRAL':
        result['error'] = 'No clear direction'
        return result

    # Get current price
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        result['error'] = 'Cannot get tick'
        return result

    entry_price = tick.ask if direction == 'BUY' else tick.bid
    atr_val = confluence['atr']

    # Calculate lot size and SL/TP
    lot, sl_dist = calc_position_size(atr_val, entry_price, direction)
    sl_tp = calc_sl_tp(entry_price, direction, atr_val)

    # Round to broker digits
    info = get_symbol_info()
    if not info:
        result['error'] = 'No symbol info'
        return result

    digits = info['digits']
    sl_price = round(sl_tp['sl'], digits)
    tp1 = round(sl_tp['tp1'], digits)

    # Prepare order request
    order_type = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
    price = tick.ask if direction == 'BUY' else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl_price,
        "tp": tp1,
        "deviation": 20,
        "magic": MAGIC,
        "comment": f"SU_V1_{direction[0]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": get_filling_mode(SYMBOL),
    }

    # Send order
    log.info(f"ENTRY|Placing {direction} {lot} lot @ {price} SL:{sl_price} TP:{tp1}")
    order_result = mt5.order_send(request)

    if order_result is None:
        result['error'] = f"Order failed (None): {mt5.last_error()}"
        log.warn(f"ENTRY|{result['error']}")
        return result

    if order_result.retcode != mt5.TRADE_RETCODE_DONE:
        result['error'] = f"Order failed: {order_result.retcode} - {order_result.comment}"
        log.warn(f"ENTRY|{result['error']}")
        return result

    result['executed'] = True
    result['ticket'] = order_result.order
    result['price'] = price
    result['lot'] = lot
    result['sl'] = sl_price
    result['tp'] = tp1

    log.info(f"ENTRY|[OK] Ticket: {order_result.order} | {direction} {lot} lot @ {price}")
    daily_state['trades_today'] += 1

    return result
