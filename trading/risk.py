"""
SNIPER ULTRA — Risk Management ($500, 1:2000, XAUUSD)
"""
from config import (
    ACCOUNT_BALANCE, RISK_PER_TRADE, MAX_RISK_DAILY,
    LOT_MIN, LOT_MAX, LOT_STEP, LEVERAGE,
    SL_ATR_MULT, SL_MIN, SL_MAX, TP_MIN_RR, TP_IDEAL_RR,
    SR_ZONE_TOLERANCE, CIRCUIT_BREAKER_LOSSES, DAILY_MAX_LOSS
)
from engine.data import get_symbol_info, calc_atr, get_open_positions
from utils.logger import log


def calc_position_size(atr_val, entry_price, direction, sr_context=None):
    """Calculate optimal lot size based on risk"""
    # Get symbol info
    info = get_symbol_info()
    if not info:
        log.warn("RISK|Cannot get symbol info, using min lot")
        return LOT_MIN

    contract_size = info['contract_size']  # 100 for XAUUSD
    balance = ACCOUNT_BALANCE
    risk_amount = balance * RISK_PER_TRADE  # $500 * 0.015 = $7.50

    # Calculate SL distance
    if sr_context and sr_context.get('sl_price'):
        # S&R-based SL
        sl_dist = abs(entry_price - sr_context['sl_price'])
    else:
        # ATR-based SL
        sl_dist = atr_val * SL_ATR_MULT

    # Clamp SL distance
    sl_dist = max(SL_MIN, min(sl_dist, SL_MAX))

    # Calculate lot: risk_amount / (sl_dist * contract_size)
    # For XAUUSD: 1 lot = 100 oz, $1 move = $100 P&L
    lot = risk_amount / (sl_dist * contract_size)
    lot = max(LOT_MIN, min(lot, LOT_MAX))

    # Round to step
    lot = round(lot / LOT_STEP) * LOT_STEP
    lot = max(LOT_MIN, lot)

    return lot, sl_dist


def calc_sl_tp(entry_price, direction, atr_val, sr_context=None):
    """Calculate SL and TP prices"""
    if sr_context and sr_context.get('sl_price'):
        if direction == 'BUY':
            sl_price = sr_context['sl_price'] - SR_ZONE_TOLERANCE
        else:
            sl_price = sr_context['sl_price'] + SR_ZONE_TOLERANCE
        sl_dist = abs(entry_price - sl_price)
        sl_dist = max(SL_MIN, min(sl_dist, SL_MAX))
    else:
        sl_dist = atr_val * SL_ATR_MULT
        sl_dist = max(SL_MIN, min(sl_dist, SL_MAX))

    sl_dist = atr_val * SL_ATR_MULT
    sl_dist = max(SL_MIN, min(sl_dist, SL_MAX))

    if direction == 'BUY':
        sl = entry_price - sl_dist
        tp1 = entry_price + sl_dist * TP_MIN_RR
        tp2 = entry_price + sl_dist * TP_IDEAL_RR
    else:
        sl = entry_price + sl_dist
        tp1 = entry_price - sl_dist * TP_MIN_RR
        tp2 = entry_price - sl_dist * TP_IDEAL_RR

    return {
        'sl': round(sl, 2),
        'tp1': round(tp1, 2),
        'tp2': round(tp2, 2),
        'sl_dist': round(sl_dist, 2),
        'rr': round(sl_dist * TP_MIN_RR / sl_dist, 1) if sl_dist > 0 else 0,
    }


def check_daily_limits(daily_pnl, daily_losses, consecutive_losses):
    """Check circuit breakers and daily limits"""
    status = {'can_trade': True, 'reason': ''}

    # Circuit breaker: consecutive losses
    if consecutive_losses >= CIRCUIT_BREAKER_LOSSES:
        status['can_trade'] = False
        status['reason'] = f"Circuit breaker: {consecutive_losses} consecutive losses"
        return status

    # Max daily loss
    if daily_pnl <= -DAILY_MAX_LOSS:
        status['can_trade'] = False
        status['reason'] = f"Daily loss limit: ${daily_pnl:.2f}"
        return status

    # Max positions
    positions = get_open_positions()
    if len(positions) >= MAX_OPEN_TRADES:
        status['can_trade'] = False
        status['reason'] = f"Max positions: {len(positions)}/{MAX_OPEN_TRADES}"

    return status


def get_risk_summary():
    """Get formatted risk summary"""
    info = get_symbol_info()
    positions = get_open_positions()

    return {
        'balance': info['balance'] if info else 0,
        'open_positions': len(positions) if positions else 0,
        'max_positions': MAX_OPEN_TRADES,
        'risk_per_trade': f"${ACCOUNT_BALANCE * RISK_PER_TRADE:.2f}",
        'daily_max_loss': f"${DAILY_MAX_LOSS}",
    }
