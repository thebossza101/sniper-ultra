"""
SNIPER ULTRA — Fibonacci Engine (Retracement, Extension, Harmonic, Cluster)
"""
import numpy as np

def find_swing_high_low(df, lookback=3):
    """Find swing highs (higher than N neighbors each side) and lows"""
    if df is None or len(df) < lookback * 2 + 1:
        return {'highs': [], 'lows': [], 'last_swing_high': 0, 'last_swing_low': 0}

    highs, lows = [], []
    prices = df['high'].values
    lows_p = df['low'].values
    idx = range(len(df))

    for i in range(lookback, len(df) - lookback):
        # Swing high: higher than lookback candles on each side
        if all(prices[i] > prices[j] for j in range(i-lookback, i)) and \
           all(prices[i] > prices[j] for j in range(i+1, i+lookback+1)):
            highs.append((int(i), float(prices[i]), str(df.iloc[i]['time'])))
        # Swing low: lower than lookback candles on each side
        if all(lows_p[i] < lows_p[j] for j in range(i-lookback, i)) and \
           all(lows_p[i] < lows_p[j] for j in range(i+1, i+lookback+1)):
            lows.append((int(i), float(lows_p[i]), str(df.iloc[i]['time'])))

    return {
        'highs': highs,
        'lows': lows,
        'last_swing_high': float(highs[-1][1]) if highs else 0,
        'last_swing_low': float(lows[-1][1]) if lows else 0,
    }


def fib_retracement(swing_high, swing_low, current_price):
    """Calculate fib retracement levels from swing range"""
    levels = [0.236, 0.382, 0.500, 0.618, 0.764, 0.786]
    diff = swing_high - swing_low
    if diff <= 0:
        return {'levels': {}, 'current_level': '', 'current_ratio': 0, 'in_ote': False}

    result_levels = {}
    for l in levels:
        result_levels[l] = round(swing_high - diff * l, 2)

    # Where is current price relative to levels?
    ratio = (swing_high - current_price) / diff if diff > 0 else 0
    ratio = max(0, min(1, ratio))

    # Find nearest level
    nearest = ''
    min_dist = 999
    for l, price in result_levels.items():
        dist = abs(current_price - price)
        if dist < min_dist:
            min_dist = dist
            nearest = f"{l*100:.1f}%"

    in_ote = 0.618 <= ratio <= 0.786

    return {
        'levels': {f"{k*100:.1f}%": v for k, v in result_levels.items()},
        'current_ratio': round(ratio, 3),
        'current_level': nearest,
        'in_ote': in_ote,
        'ote_low': round(swing_high - diff * 0.786, 2),
        'ote_high': round(swing_high - diff * 0.618, 2),
        'swing_high': swing_high,
        'swing_low': swing_low,
    }


def fib_extension(swing_high, swing_low, retracement_low=None):
    """Calculate fib extension targets"""
    diff = swing_high - swing_low
    if diff <= 0:
        return {}

    ext_levels = [0.382, 0.618, 1.0, 1.272, 1.382, 1.618, 2.0, 2.618]
    return {
        f"{k*100:.1f}%": round(swing_high + diff * k, 2)
        for k in ext_levels
    }


def detect_harmonic_pattern(df):
    """
    Basic harmonic pattern detection: Gartley, Bat, Butterfly, Crab
    Uses fib ratios between swing points
    """
    result = {'detected': False, 'pattern': '', 'direction': '', 'entry': 0, 'sl': 0, 'tp': 0, 'confidence': 0}

    swing = find_swing_high_low(df, lookback=3)

    # Need minimum 4 swing points: X-A-B-C-D
    # For bullish: X=low, A=high, B=low, C=high, D=low (predicted)
    # We'll do basic detection with what we have
    if len(swing['highs']) < 2 or len(swing['lows']) < 2:
        return result

    # Get last 2 highs and 2 lows
    h2 = swing['highs'][-2][1] if len(swing['highs']) >= 2 else 0
    h1 = swing['highs'][-1][1] if swing['highs'] else 0
    l2 = swing['lows'][-2][1] if len(swing['lows']) >= 2 else 0
    l1 = swing['lows'][-1][1] if swing['lows'] else 0

    # Not enough data
    if not all([h2, h1, l2, l1]):
        return result

    # Check patterns
    # Gartley: XA retrace to B at 0.618, BC retrace to C at 0.382-0.886, CD extension 1.272-1.618
    xa_range = h2 - l2
    if xa_range > 0:
        ab_ratio = (h2 - l1) / xa_range
        # Bullish Gartley pattern
        if 0.618 - 0.05 <= ab_ratio <= 0.618 + 0.05:
            result['detected'] = True
            result['pattern'] = 'GARTLEY'
            result['direction'] = 'BUY'
            result['entry'] = round(l1, 2)
            result['sl'] = round(l2 - xa_range * 0.1, 2)
            result['tp'] = round(h2 + xa_range * 0.618, 2)
            result['confidence'] = 7

    return result


def fib_cluster(swing_high, swing_low, retracement_low, current_price):
    """Find fib cluster areas (multiple ratios close together = strong zone)"""
    diff = swing_high - swing_low
    if diff <= 0:
        return {'cluster_levels': [], 'best_cluster': {'price': 0, 'strength': 0}}

    all_levels = []
    # Retracement levels
    ret_levels = [0.236, 0.382, 0.5, 0.618, 0.764, 0.786]
    for l in ret_levels:
        all_levels.append((swing_high - diff * l, f"RET {l*100:.1f}%"))
    # Extension levels
    ext_levels = [0.382, 0.618, 1.0, 1.272, 1.618]
    for l in ext_levels:
        all_levels.append((swing_high + diff * l, f"EXT {l*100:.1f}%"))

    # Find clusters (levels within 0.5% of each other)
    all_levels.sort(key=lambda x: x[0])
    clusters = []
    current_cluster = [all_levels[0]] if all_levels else []

    for i in range(1, len(all_levels)):
        price_diff = abs(all_levels[i][0] - all_levels[i-1][0])
        if price_diff / swing_high < 0.005:  # 0.5% tolerance
            current_cluster.append(all_levels[i])
        else:
            if len(current_cluster) >= 2:
                avg_price = sum(p for p, _ in current_cluster) / len(current_cluster)
                clusters.append((avg_price, len(current_cluster)))
            current_cluster = [all_levels[i]]

    if len(current_cluster) >= 2:
        avg_price = sum(p for p, _ in current_cluster) / len(current_cluster)
        clusters.append((avg_price, len(current_cluster)))

    clusters.sort(key=lambda x: abs(x[0] - current_price))

    return {
        'cluster_levels': [(round(p, 2), s) for p, s in clusters],
        'best_cluster': {'price': round(clusters[0][0], 2), 'strength': clusters[0][1]}
        if clusters else {'price': 0, 'strength': 0},
    }


def analyze_fib(df, direction=None):
    """Wrapper: complete fib analysis"""
    if df is None or len(df) < 10:
        return {'detected': False, 'in_ote': False, 'current_ratio': 0,
                'ote_low': 0, 'ote_high': 0, 'cluster': {}, 'harmonic': {}, 'score': 0}

    swing = find_swing_high_low(df, lookback=3)
    current_price = float(df.iloc[-1]['close'])

    if swing['last_swing_high'] == 0 or swing['last_swing_low'] == 0:
        return {'detected': False, 'in_ote': False, 'current_ratio': 0,
                'ote_low': 0, 'ote_high': 0, 'cluster': {}, 'harmonic': {}, 'score': 0}

    sh, sl = swing['last_swing_high'], swing['last_swing_low']

    # Determine direction: if last move was up, use high->low fib for retracement
    if sh > sl:
        ret = fib_retracement(sh, sl, current_price)
    else:
        ret = fib_retracement(sl, sh, current_price)

    harmonic = detect_harmonic_pattern(df)
    cluster = fib_cluster(sh, sl, current_price, current_price)

    # Score: 0-20
    score = 0
    if ret['in_ote']:
        score += 15
    elif 0.382 <= ret['current_ratio'] <= 0.618:
        score += 10
    if harmonic['detected']:
        score += 5
    if cluster['best_cluster']['strength'] >= 2:
        score += 5

    return {
        'detected': True,
        'in_ote': ret['in_ote'],
        'current_ratio': ret['current_ratio'],
        'current_level': ret['current_level'],
        'ote_low': ret['ote_low'],
        'ote_high': ret['ote_high'],
        'levels': ret['levels'],
        'harmonic': harmonic,
        'cluster': cluster,
        'score': min(score, 20),
    }
