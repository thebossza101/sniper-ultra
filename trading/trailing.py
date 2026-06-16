"""
SNIPER ULTRA — Smart Trailing Stop (25% Increment)
"""
import MetaTrader5 as mt5
from config import SYMBOL, MAGIC, TRAILING_STAGES
from engine.data import calc_atr, get_data, get_open_positions
from utils.logger import log


def smart_trail_position(pos, current_price, atr_val):
    """
    Smart trailing with 25% profit increments
    
    Calculates ALL stages, picks BEST SL (highest for BUY, lowest for SELL)
    """
    if atr_val <= 0:
        return None, ''

    direction = 'BUY' if pos.type == 0 else 'SELL'
    entry = pos.price_open
    current_sl = pos.sl

    if direction == 'BUY':
        profit = current_price - entry
    else:
        profit = entry - current_price

    sl_dist = abs(entry - current_sl) if current_sl else atr_val * 1.5
    if sl_dist <= 0:
        sl_dist = atr_val * 1.5

    profit_pct = profit / sl_dist if sl_dist > 0 else 0

    best_sl = current_sl
    best_reason = ''

    for stage_pct, atr_mult, name in TRAILING_STAGES:
        if profit_pct >= stage_pct:
            if direction == 'BUY':
                if stage_pct == 0.25:  # Breakeven
                    new_sl = entry + atr_val * 0.1  # Slightly above entry
                else:
                    new_sl = current_price - atr_val * atr_mult

                if best_sl is None or new_sl > best_sl:
                    best_sl = new_sl
                    best_reason = f"Trail {name}"

            else:  # SELL
                if stage_pct == 0.25:
                    new_sl = entry - atr_val * 0.1
                else:
                    new_sl = current_price + atr_val * atr_mult

                if best_sl is None or new_sl < best_sl:
                    best_sl = new_sl
                    best_reason = f"Trail {name}"

    # Only update if SL is better than current
    if direction == 'BUY' and (best_sl is not None and best_sl > current_sl):
        return best_sl, best_reason
    elif direction == 'SELL' and (best_sl is not None and (current_sl == 0 or best_sl < current_sl)):
        return best_sl, best_reason

    return None, ''


def manage_smart_trailing(data_dict=None):
    """Run trailing on all open positions"""
    positions = get_open_positions()
    if not positions:
        return 0

    atr_val = calc_atr(get_data("M15")) if data_dict is None else \
              calc_atr(data_dict.get('M15'))

    if atr_val == 0:
        return 0

    modified = 0

    for pos in positions:
        if pos.magic != MAGIC:
            continue

        current_price = pos.price_current
        new_sl, reason = smart_trail_position(pos, current_price, atr_val)

        if new_sl is not None and new_sl != pos.sl:
            # Round to broker digits
            info_data = getattr(mt5, 'symbol_info_tick', lambda x: None)(SYMBOL)
            info = getattr(mt5, 'symbol_info', lambda x: None)(SYMBOL)
            digits = info.digits if info else 2

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": SYMBOL,
                "position": pos.ticket,
                "sl": round(new_sl, digits),
                "tp": pos.tp,
            }

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                modified += 1
                log.info(f"TRAIL|Pos {pos.ticket} SL moved: {pos.sl:.2f} -> {new_sl:.2f} ({reason})")
            else:
                err = mt5.last_error()
                log.warn(f"TRAIL|Pos {pos.ticket} failed: {err}")

    return modified
