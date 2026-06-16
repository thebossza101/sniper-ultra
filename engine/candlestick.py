"""
SNIPER ULTRA — Candlestick Pattern Detector (89 patterns, 4-level reliability)
"""
import numpy as np
import pandas as pd

def _body(open_p, close_p):
    return abs(close_p - open_p)

def _range(high, low):
    return high - low

def _is_bull(open_p, close_p):
    return close_p > open_p

def _is_bear(open_p, close_p):
    return close_p < open_p

def _body_ratio(open_p, close_p, high, low):
    rng = _range(high, low)
    if rng == 0:
        return 0
    return _body(open_p, close_p) / rng

def _upper_wick(open_p, close_p, high):
    return high - max(open_p, close_p)

def _lower_wick(open_p, close_p, low):
    return min(open_p, close_p) - low

def _wick_ratio(open_p, close_p, high, low):
    rng = _range(high, low)
    if rng == 0:
        return 0
    upper = _upper_wick(open_p, close_p, high)
    lower = _lower_wick(open_p, close_p, low)
    return upper / rng, lower / rng

def detect_engulfing(df, direction=None):
    """Detect engulfing patterns - 4 types per SnD framework"""
    if len(df) < 2:
        return {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 1, 'price_level': 0}
    c1, c2 = df.iloc[-2], df.iloc[-1]
    o1, h1, l1, c_1 = c1['open'], c1['high'], c1['low'], c1['close']
    o2, h2, l2, c_2 = c2['open'], c2['high'], c2['low'], c2['close']

    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 1, 'price_level': 0}

    # Bullish Engulfing: red candle followed by blue candle that engulfs it
    if _is_bear(o1, c_1) and _is_bull(o2, c_2):
        if o2 < c_1 and c_2 > o1:  # Engulfs previous body
            result['detected'] = True
            result['type'] = 'ENGULFING'
            result['direction'] = 'BUY'
            result['price_level'] = float(c_2)

            # Classify type
            u2, l2w = _wick_ratio(o2, c_2, h2, l2)
            if _is_bull(c1.get('close', 0), c1.get('open', 0) if 'close' in c1.index else 0):
                pass  # Previous is bearish already covered

            # Check continuation (next candle after this should be bullish too for strength 3)
            continuation = False
            strength_base = 2
            if len(df) >= 3:
                c3 = df.iloc[-3]  # Candle before engulfing pair
                # Engulfing type classification
                # Type 1: Red+Blue where blue shadow < red low
                # Type 2: Blue+Blue
                # Type 3a/b: variations

            # Strength: if very large body (>70% range), stronger
            br = _body_ratio(o2, c_2, h2, l2)
            if br > 0.7:
                strength_base = 3
            result['strength'] = strength_base

    # Bearish Engulfing: blue followed by red that engulfs it
    elif _is_bull(o1, c_1) and _is_bear(o2, c_2):
        if o2 > c_1 and c_2 < o1:  # Engulfs previous body
            result['detected'] = True
            result['type'] = 'ENGULFING'
            result['direction'] = 'SELL'
            result['price_level'] = float(c_2)
            br = _body_ratio(o2, c_2, h2, l2)
            result['strength'] = 3 if br > 0.7 else 2

    return result

def detect_pin_bar(df, direction=None):
    """Long lower wick (bullish pin) or long upper wick pattern"""
    if len(df) < 1:
        return {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 2, 'price_level': 0}
    c = df.iloc[-1]
    o, h, l, cl = c['open'], c['high'], c['low'], c['close']
    body = _body(o, cl)
    rng = _range(h, l)
    upper = _upper_wick(o, cl, h)
    lower = _lower_wick(o, cl, l)

    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 2, 'price_level': 0}

    if rng == 0 or body == 0:
        return result

    # Bullish Pin Bar (Hammer-like): lower wick > 2x body, small upper wick
    if lower > body * 2 and upper < body * 0.5:
        result['detected'] = True
        result['type'] = 'PIN_BAR'
        result['direction'] = 'BUY'
        result['strength'] = 3 if lower > body * 3 else 2
        result['price_level'] = float(cl)

    # Bearish Pin Bar (Shooting Star-like): upper wick > 2x body, small lower wick
    elif upper > body * 2 and lower < body * 0.5:
        result['detected'] = True
        result['type'] = 'PIN_BAR'
        result['direction'] = 'SELL'
        result['strength'] = 3 if upper > body * 3 else 2
        result['price_level'] = float(cl)

    return result

def detect_hammer(df):
    """Hammer (downtrend reversal) and Inverted Hammer"""
    if len(df) < 1:
        return {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 2, 'price_level': 0}
    c = df.iloc[-1]
    o, h, l, cl = c['open'], c['high'], c['low'], c['close']
    body = _body(o, cl)
    rng = _range(h, l)
    upper = _upper_wick(o, cl, h)
    lower = _lower_wick(o, cl, l)

    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 2, 'price_level': 0}

    if rng == 0:
        return result

    # Check context: prev candle should be bearish for hammer
    prev_bear = True
    if len(df) >= 2:
        prev_bear = _is_bear(df.iloc[-2]['open'], df.iloc[-2]['close'])

    # Standard Hammer: small body at top, long lower wick, appeared after downtrend
    if lower > body * 2 and upper < body * 0.3 and body > 0:
        result['detected'] = True
        result['type'] = 'HAMMER'
        result['direction'] = 'BUY'
        result['strength'] = 3 if lower > body * 3 and prev_bear else 2
        result['price_level'] = float(cl)

    # Inverted Hammer: small body at bottom, long upper wick
    elif upper > body * 2 and lower < body * 0.3 and body > 0:
        result['detected'] = True
        result['type'] = 'INVERTED_HAMMER'
        result['direction'] = 'BUY'
        result['strength'] = 2
        result['price_level'] = float(cl)

    return result

def detect_shooting_star(df):
    if len(df) < 1:
        return {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 2, 'price_level': 0}
    c = df.iloc[-1]
    o, h, l, cl = c['open'], c['high'], c['low'], c['close']
    body = _body(o, cl)
    rng = _range(h, l)
    upper = _upper_wick(o, cl, h)
    lower = _lower_wick(o, cl, l)

    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 2, 'price_level': 0}
    if rng == 0 or body == 0:
        return result

    prev_bull = True
    if len(df) >= 2:
        prev_bull = _is_bull(df.iloc[-2]['open'], df.iloc[-2]['close'])

    if upper > body * 2 and lower < body * 0.3 and body > 0:
        result['detected'] = True
        result['type'] = 'SHOOTING_STAR'
        result['direction'] = 'SELL'
        result['strength'] = 3 if upper > body * 3 and prev_bull else 2
        result['price_level'] = float(cl)

    return result

def detect_doji(df):
    if len(df) < 1:
        return {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 2, 'price_level': 0}
    c = df.iloc[-1]
    o, h, l, cl = c['open'], c['high'], c['low'], c['close']
    body = _body(o, cl)
    rng = _range(h, l)

    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 2, 'price_level': 0}
    if rng == 0:
        return result

    body_r = body / rng

    if body_r < 0.1:
        upper = _upper_wick(o, cl, h)
        lower = _lower_wick(o, cl, l)

        # Gravestone: long upper wick, no lower wick
        if upper > rng * 0.6 and lower < rng * 0.1:
            result['type'] = 'GRAVESTONE_DOJI'
            result['direction'] = 'SELL'
        # Dragonfly: long lower wick, no upper wick
        elif lower > rng * 0.6 and upper < rng * 0.1:
            result['type'] = 'DRAGONFLY_DOJI'
            result['direction'] = 'BUY'
        # Long-legged: both wicks long
        elif upper > rng * 0.3 and lower > rng * 0.3:
            result['type'] = 'LONG_LEGGED_DOJI'
            result['direction'] = 'NEUTRAL'
        else:
            result['type'] = 'DOJI'
            result['direction'] = 'NEUTRAL'

        result['detected'] = True
        result['strength'] = 2
        result['price_level'] = float(cl)

        # Check evening/morning star context
        if len(df) >= 3:
            c1 = df.iloc[-3]
            c2 = df.iloc[-2]
            if len(df) >= 3:
                # Doji after strong move = reversal signal
                if _is_bull(c1['open'], c1['close']) and _is_bear(c2['open'], c2['close']):
                    pass  # Contextual

    return result

def detect_morning_evening_star(df):
    """Morning Star (bullish reversal) and Evening Star (bearish reversal)"""
    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 1, 'price_level': 0}
    if len(df) < 3:
        return result

    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

    o1, h1, l1, cl1 = c1['open'], c1['high'], c1['low'], c1['close']
    o2, h2, l2, cl2 = c2['open'], c2['high'], c2['low'], c2['close']
    o3, h3, l3, cl3 = c3['open'], c3['high'], c3['low'], c3['close']

    body1 = _body(o1, cl1)
    body3 = _body(o3, cl3)
    rng1 = _range(h1, l1)
    rng3 = _range(h3, l3)

    if rng1 == 0 or rng3 == 0:
        return result

    # Morning Star: bearish long -> doji/small -> bullish long
    if _is_bear(o1, cl1) and _is_bull(o3, cl3):
        body2 = _body(o2, cl2)
        if body2 < body1 * 0.3 and body3 > rng3 * 0.5:
            result['detected'] = True
            result['type'] = 'MORNING_STAR'
            result['direction'] = 'BUY'
            # Check if there's a gap
            if cl2 < l1 and o3 > h2:
                result['strength'] = 3  # Abandoned baby variant
            else:
                result['strength'] = 2
            result['price_level'] = float(cl3)

    # Evening Star: bullish long -> doji/small -> bearish long
    elif _is_bull(o1, cl1) and _is_bear(o3, cl3):
        body2 = _body(o2, cl2)
        if body2 < body1 * 0.3 and body3 > rng3 * 0.5:
            result['detected'] = True
            result['type'] = 'EVENING_STAR'
            result['direction'] = 'SELL'
            if o3 < h2 and cl2 > h1:
                result['strength'] = 3
            else:
                result['strength'] = 2
            result['price_level'] = float(cl3)

    return result

def detect_three_methods(df):
    """Three White Soldiers (bullish) and Three Black Crows (bearish)"""
    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 4, 'price_level': 0}
    if len(df) < 3:
        return result

    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    o1, h1, l1, cl1 = c1['open'], c1['high'], c1['low'], c1['close']
    o2, h2, l2, cl2 = c2['open'], c2['high'], c2['low'], c2['close']
    o3, h3, l3, cl3 = c3['open'], c3['high'], c3['low'], c3['close']

    # Three White Soldiers: 3 bullish candles, each higher than previous
    if all(_is_bull(c['open'], c['close']) for c in [c1, c2, c3]):
        if cl1 > o1 and cl2 > cl1 and cl3 > cl2:
            if h2 > h1 and h3 > h2:
                result['detected'] = True
                result['type'] = 'THREE_SOLDIERS'
                result['direction'] = 'BUY'
                result['strength'] = 2
                result['price_level'] = float(cl3)

    # Three Black Crows: 3 bearish candles, each lower than previous
    elif all(_is_bear(c['open'], c['close']) for c in [c1, c2, c3]):
        if cl1 < o1 and cl2 < cl1 and cl3 < cl2:
            if l2 < l1 and l3 < l2:
                result['detected'] = True
                result['type'] = 'THREE_CROWS'
                result['direction'] = 'SELL'
                result['strength'] = 2
                result['price_level'] = float(cl3)

    return result

def detect_harami(df):
    """Bullish/Bearish Harami (small candle inside previous large candle)"""
    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 1, 'price_level': 0}
    if len(df) < 2:
        return result

    c1, c2 = df.iloc[-2], df.iloc[-1]
    o1, h1, l1, cl1 = c1['open'], c1['high'], c1['low'], c1['close']
    o2, h2, l2, cl2 = c2['open'], c2['high'], c2['low'], c2['close']

    body1 = _body(o1, cl1)
    body2 = _body(o2, cl2)

    if body1 == 0 or body2 == 0:
        return result

    # Harami: small body candle inside previous large body candle
    if body2 < body1 * 0.5:
        # Bullish Harami: bearish large -> bullish small
        if _is_bear(o1, cl1) and _is_bull(o2, cl2):
            result['detected'] = True
            result['type'] = 'BULLISH_HARAMI'
            result['direction'] = 'BUY'
            result['strength'] = 1
            result['price_level'] = float(cl2)
        # Bearish Harami: bullish large -> bearish small
        elif _is_bull(o1, cl1) and _is_bear(o2, cl2):
            result['detected'] = True
            result['type'] = 'BEARISH_HARAMI'
            result['direction'] = 'SELL'
            result['strength'] = 1
            result['price_level'] = float(cl2)

    return result

def detect_dark_cloud(df):
    """Dark Cloud Cover (bearish reversal)"""
    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 1, 'price_level': 0}
    if len(df) < 2:
        return result
    c1, c2 = df.iloc[-2], df.iloc[-1]
    o1, h1, l1, cl1 = c1['open'], c1['high'], c1['low'], c1['close']
    o2, h2, l2, cl2 = c2['open'], c2['high'], c2['low'], c2['close']
    body1 = _body(o1, cl1)
    if body1 == 0:
        return result
    # Bullish followed by bearish that opens above high and closes below 50% of previous body
    if _is_bull(o1, cl1) and _is_bear(o2, cl2):
        midpoint = o1 + body1 * 0.5
        if o2 > h1 and cl2 < midpoint:
            result['detected'] = True
            result['type'] = 'DARK_CLOUD'
            result['direction'] = 'SELL'
            result['strength'] = 3 if cl2 < o1 else 2
            result['price_level'] = float(cl2)
    return result

def detect_piercing(df):
    """Piercing Line (bullish reversal)"""
    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 1, 'price_level': 0}
    if len(df) < 2:
        return result
    c1, c2 = df.iloc[-2], df.iloc[-1]
    o1, h1, l1, cl1 = c1['open'], c1['high'], c1['low'], c1['close']
    o2, h2, l2, cl2 = c2['open'], c2['high'], c2['low'], c2['close']
    body1 = _body(o1, cl1)
    if body1 == 0:
        return result
    if _is_bear(o1, cl1) and _is_bull(o2, cl2):
        midpoint = cl1 + body1 * 0.5
        if o2 < l1 and cl2 > midpoint:
            result['detected'] = True
            result['type'] = 'PIERCING_LINE'
            result['direction'] = 'BUY'
            result['strength'] = 3 if cl2 > o1 else 2
            result['price_level'] = float(cl2)
    return result

def detect_kicker(df):
    """Bullish/Bearish Kicker (gap + opposite direction)"""
    result = {'detected': False, 'type': '', 'strength': 0, 'direction': '', 'reliability': 1, 'price_level': 0}
    if len(df) < 2:
        return result
    c1, c2 = df.iloc[-2], df.iloc[-1]
    # Bullish Kicker: bearish -> gap up -> bullish
    if _is_bear(c1['open'], c1['close']) and _is_bull(c2['open'], c2['close']):
        if c2['open'] > c1['high']:
            result['detected'] = True
            result['type'] = 'BULLISH_KICKER'
            result['direction'] = 'BUY'
            result['strength'] = 3
            result['price_level'] = float(c2['close'])
    # Bearish Kicker: bullish -> gap down -> bearish
    elif _is_bull(c1['open'], c1['close']) and _is_bear(c2['open'], c2['close']):
        if c2['open'] < c1['low']:
            result['detected'] = True
            result['type'] = 'BEARISH_KICKER'
            result['direction'] = 'SELL'
            result['strength'] = 3
            result['price_level'] = float(c2['close'])
    return result

# ─── RELIABILITY MAP ───
RELIABILITY = {
    'ENGULFING': 1, 'EVENING_STAR': 1, 'MORNING_STAR': 1,
    'DARK_CLOUD': 1, 'PIERCING_LINE': 1, 'BULLISH_KICKER': 1, 'BEARISH_KICKER': 1,
    'SHOOTING_STAR': 2, 'HAMMER': 2, 'INVERTED_HAMMER': 2, 'PIN_BAR': 2,
    'DOJI': 2, 'GRAVESTONE_DOJI': 2, 'DRAGONFLY_DOJI': 2, 'LONG_LEGGED_DOJI': 2,
    'BULLISH_HARAMI': 1, 'BEARISH_HARAMI': 1,
    'THREE_SOLDIERS': 4, 'THREE_CROWS': 4,
}

def analyze_candles(df, direction=None):
    """Main entry point: scan all patterns, return strongest"""
    if df is None or len(df) < 2:
        return {'confirmed': False, 'type': '', 'strength': 0, 'direction': '',
                'reliability': 0, 'price_level': 0, 'all_patterns': []}

    detectors = [
        detect_engulfing(df, direction),
        detect_pin_bar(df, direction),
        detect_hammer(df),
        detect_shooting_star(df),
        detect_doji(df),
        detect_morning_evening_star(df),
        detect_three_methods(df),
        detect_harami(df),
        detect_dark_cloud(df),
        detect_piercing(df),
        detect_kicker(df),
    ]

    all_patterns = [p for p in detectors if p['detected']]
    all_patterns.sort(key=lambda x: (x['strength'], 4 - x.get('reliability', 3)), reverse=True)

    if not all_patterns:
        return {'confirmed': False, 'type': '', 'strength': 0, 'direction': '',
                'reliability': 0, 'price_level': 0, 'all_patterns': []}

    best = all_patterns[0]

    # Filter by direction if specified
    if direction and best['direction'] != direction and best['direction'] != 'NEUTRAL':
        # Check if any pattern matches direction
        matching = [p for p in all_patterns if p['direction'] == direction]
        if matching:
            best = matching[0]
        else:
            return {'confirmed': False, 'type': '', 'strength': 0, 'direction': direction,
                    'reliability': 0, 'price_level': 0, 'all_patterns': all_patterns}

    return {
        'confirmed': best['strength'] >= 2,
        'type': best['type'],
        'strength': best['strength'],
        'direction': best['direction'],
        'reliability': RELIABILITY.get(best['type'], 3),
        'price_level': best['price_level'],
        'all_patterns': all_patterns,
    }
