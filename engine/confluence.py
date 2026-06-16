"""
SNIPER ULTRA — Confluence v3 (SIMPLE)
Cuma 2 kondisi: Candle confirm + Arah mayoritas
"""
from engine.snd import analyze_snd
from engine.smc import analyze_smc
from engine.elliot_wave import analyze_elliot
from engine.fibonacci import analyze_fib
from engine.liquidity import analyze_liquidity
from engine.candlestick import analyze_candles
from engine.triple_screen import analyze_triple_screen
from engine.data import calc_atr


def calculate_full_confluence(data_dict, current_price):
    """
    Simple 2-condition:
    1. CANDLE: Ada pattern confirmed di M1?
    2. ALIGNMENT: Mayoritas modul setuju arah?
    
    Entry kalo 2 kondisi terpenuhi.
    """
    result = {
        'total_score': 0,
        'breakdown': {},
        'candle': {'ok': False, 'type': '', 'strength': 0, 'direction': ''},
        'alignment': {'bull': 0, 'bear': 0, 'arah': 'NEUTRAL'},
        'direction': 'NEUTRAL',
        'zone_status': 'NO_ZONE',
        'recommendation': 'WAIT',
        'atr': 0,
    }

    if not data_dict or current_price == 0:
        return result

    h1_df = data_dict.get('H1')
    m15_df = data_dict.get('M15')
    m5_df = data_dict.get('M5')
    m1_df = data_dict.get('M1')
    mtf_df = m15_df if m15_df is not None else m5_df

    # ─── JALANKAN 7 MODUL ───
    # NOTE: The ternary 'x if x else y' checks DataFrame truthiness == pandas crash.
    # Always use 'is not None' when DataFrames can be None.
    _h1 = h1_df if h1_df is not None else mtf_df
    _mtf = mtf_df if mtf_df is not None else h1_df
    _m5 = m5_df if m5_df is not None else mtf_df
    _m1 = m1_df if m1_df is not None else m5_df

    snd = analyze_snd(_h1, current_price)
    smc = analyze_smc(_mtf, current_price)
    elliot = analyze_elliot(_h1)
    fib = analyze_fib(_mtf)
    liq = analyze_liquidity(_m5, current_price)
    candle = analyze_candles(_m1)
    ts = analyze_triple_screen(data_dict)

    result['breakdown'] = {
        'snd': {'score': snd['score'], 'zone': snd['zone_status']},
        'smc': {'score': smc['score'], 'trend': smc['structure']['trend']},
        'elliot': {'score': elliot['score'], 'wave': elliot['wave_count']['in_wave']},
        'fib': {'score': fib['score'], 'ote': fib['in_ote']},
        'liq': {'score': liq['score'], 'sweep': liq['has_recent_sweep']},
        'cdl': {'type': candle['type'], 'str': candle['strength'], 'ok': candle['confirmed']},
        'ts': {'htf': ts['htf_impulse']['signal'], 'ltf': ts['ltf_impulse']['signal']},
    }

    atr_val = calc_atr(mtf_df) if mtf_df is not None else 0
    result['atr'] = round(atr_val, 2)
    result['zone_status'] = snd['zone_status']

    # ─── KONDISI 1: CANDLE ───
    candle_ok = candle['confirmed'] and candle['strength'] >= 2
    result['candle'] = {
        'ok': candle_ok,
        'type': candle['type'],
        'strength': candle['strength'],
        'direction': candle['direction'],
    }

    # ─── KONDISI 2: ALIGNMENT (voting) ───
    buy = 0
    sell = 0

    # Tiap modul kasih suara (1=BUY, -1=SELL, 0=NETRAL)
    # SnD
    if snd['zone_status'] == 'BUY_ZONE': buy += 1
    elif snd['zone_status'] == 'SELL_ZONE': sell += 1

    # SMC
    if smc['in_bullish_ob']: buy += 2
    elif smc['in_bearish_ob']: sell += 2
    elif smc['structure']['trend'] == 'BULL': buy += 1
    elif smc['structure']['trend'] == 'BEAR': sell += 1

    # Elliot
    if elliot['alignment'] == 'BULLISH': buy += 1
    elif elliot['alignment'] == 'BEARISH': sell += 1

    # Liquidity
    if liq['sweep'] and liq['sweep'].get('direction') == 'BUY': buy += 1
    elif liq['sweep'] and liq['sweep'].get('direction') == 'SELL': sell += 1

    # Triple Screen
    al = ts['triple_screen']['alignment']
    if al == 'FULL_BULL': buy += 2
    elif al == 'FULL_BEAR': sell += 2
    elif al == 'PULLBACK_BULL': buy += 1
    elif al == 'BOUNCE_ONLY': sell += 1

    # Fib di OTE = konfirmasi (tambah ke yang lebih kuat)
    if fib['in_ote']:
        if buy > sell: buy += 1
        elif sell > buy: sell += 1

    result['alignment'] = {'bull': buy, 'bear': sell}

    # Tentukan arah
    if buy > sell and buy >= 3:
        arah = 'BUY'
    elif sell > buy and sell >= 3:
        arah = 'SELL'
    else:
        arah = 'NEUTRAL'

    result['direction'] = arah

    # ─── KEPUTUSAN ───
    if candle_ok and arah != 'NEUTRAL' and candle['direction'] == arah:
        result['recommendation'] = 'ENTRY'
    elif candle_ok and arah != 'NEUTRAL' and candle['direction'] != arah:
        result['recommendation'] = 'MISALIGNED'
    elif not candle_ok and arah != 'NEUTRAL':
        result['recommendation'] = 'NO_CANDLE'
    else:
        result['recommendation'] = 'WAIT'

    # Total score (buat referensi)
    total = snd['score'] + smc['score'] + elliot['score'] + fib['score'] + \
            liq['score'] + (candle['strength'] * 10 if candle['confirmed'] else 0) + ts['score']
    result['total_score'] = min(total, 200)

    return result
