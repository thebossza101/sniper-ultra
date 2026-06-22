"""
SNIPER ULTRA — MT5 Data Connector
Fetch OHLCV multi-TF, ATR, symbol info
"""
try:
    import MetaTrader5 as mt5
except ImportError:
    # MetaTrader5 hanya tersedia di Windows. Mode offline (test.py) tidak butuh mt5,
    # cukup fungsi murni seperti calc_atr. Fungsi yang pakai mt5 akan error saat dipanggil.
    mt5 = None
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from config import SYMBOL, TF_MAP, MAGIC, LEVERAGE

def mt5_connect(login, password, server):
    """Connect to MT5"""
    if not mt5.initialize():
        return False, f"MT5 init failed: {mt5.last_error()}"
    authorized = mt5.login(login=login, password=password, server=server)
    if not authorized:
        return False, f"MT5 login failed: {mt5.last_error()}"
    return True, f"Connected: {mt5.account_info().balance}"

def mt5_disconnect():
    mt5.shutdown()

def get_data(tf_str="M1", count=200):
    """Fetch OHLCV dari MT5. Returns DataFrame atau None"""
    tf = TF_MAP.get(tf_str)
    if not tf:
        return None
    tf_mt5 = getattr(mt5, f"TIMEFRAME_{tf_str}", None)
    if tf_mt5 is None:
        return None
    rates = mt5.copy_rates_from_pos(SYMBOL, tf_mt5, 0, count)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.attrs["tf"] = tf_str
    return df

def get_multi_tf_data(htf_count=200, mtf_count=200, stf_count=150, ltf_count=100):
    """Fetch semua timeframe sekaligus"""
    return {
        "H1": get_data("H1", htf_count),
        "M15": get_data("M15", mtf_count),
        "M5": get_data("M5", stf_count),
        "M1": get_data("M1", ltf_count),
    }

def calc_atr(df, period=14):
    """True Range ATR"""
    if df is None or len(df) < period + 1:
        return 0.0
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(
        np.abs(high - prev_close), np.abs(low - prev_close)
    ))
    atr = np.mean(tr[-period:])
    return atr

def get_symbol_info():
    """Dapatkan info symbol: spread, digits, contract size, min/max lot"""
    info = mt5.symbol_info(SYMBOL)
    if info is None:
        return None
    tick = mt5.symbol_info_tick(SYMBOL)
    return {
        "spread": info.spread,
        "digits": info.digits,
        "point": info.point,
        "contract_size": info.trade_contract_size,
        "volume_min": info.volume_min,
        "volume_max": info.volume_max,
        "volume_step": info.volume_step,
        "bid": tick.bid if tick else 0,
        "ask": tick.ask if tick else 0,
    }

def get_open_positions():
    """Dapatkan open positions bot ini"""
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        return []
    return [p for p in positions if p.magic == MAGIC]

def get_account_info():
    acc = mt5.account_info()
    if acc is None:
        return None
    return {
        "balance": acc.balance,
        "equity": acc.equity,
        "margin": acc.margin,
        "margin_free": acc.margin_free,
        "leverage": acc.leverage,
    }

def check_mt5_health():
    """Cek koneksi MT5 — reconnect jika perlu"""
    acc = mt5.account_info()
    if acc is None:
        from utils.logger import log
        log.warn("MT5 disconnected - reconnecting...")
        mt5.shutdown()
        import time
        time.sleep(3)
        return False
    return True
