"""
SNIPER ULTRA — Liquidity Engine (Pools, Sweeps, Inducement, Session Levels)
"""
import numpy as np

def find_equal_highs_lows(df, tolerance=0.002, lookback=30):
    """Find equal highs (BSL) and equal lows (SSL)"""
    result = {'bsl_zones': [], 'ssl_zones': []}

    if df is None or len(df) < 5:
        return result

    highs = df['high'].values[-lookback:]
    lows = df['low'].values[-lookback:]

    # Find equal highs (within tolerance)
    bsl_candidates = {}
    for i in range(len(highs)):
        for j in range(i+1, len(highs)):
            if highs[i] > 0 and abs(highs[i] - highs[j]) / highs[i] < tolerance:
                avg_price = (highs[i] + highs[j]) / 2
                key = round(avg_price, 1)
                if key not in bsl_candidates:
                    bsl_candidates[key] = {'price': avg_price, 'count': 0, 'indices': []}
                bsl_candidates[key]['count'] += 1
                bsl_candidates[key]['indices'].extend([i, j])

    # Find equal lows
    ssl_candidates = {}
    for i in range(len(lows)):
        for j in range(i+1, len(lows)):
            if lows[i] > 0 and abs(lows[i] - lows[j]) / lows[i] < tolerance:
                avg_price = (lows[i] + lows[j]) / 2
                key = round(avg_price, 1)
                if key not in ssl_candidates:
                    ssl_candidates[key] = {'price': avg_price, 'count': 0, 'indices': []}
                ssl_candidates[key]['count'] += 1
                ssl_candidates[key]['indices'].extend([i, j])

    # Filter: minimum 2 touches
    result['bsl_zones'] = [
        {'price': float(v['price']), 'count': int(v['count'])}
        for v in bsl_candidates.values() if v['count'] >= 2
    ]
    result['ssl_zones'] = [
        {'price': float(v['price']), 'count': int(v['count'])}
        for v in ssl_candidates.values() if v['count'] >= 2
    ]

    # Sort by count (most touched first)
    result['bsl_zones'].sort(key=lambda x: x['count'], reverse=True)
    result['ssl_zones'].sort(key=lambda x: x['count'], reverse=True)

    return result


def find_session_levels(df):
    """Find PDH/PDL and session highs/lows"""
    result = {'pdh': 0, 'pdl': 0, 'asian_high': 0, 'asian_low': 0,
              'london_high': 0, 'london_low': 0}

    if df is None or len(df) < 10:
        return result

    # For simplicity: use last ~24 candles as "previous day"
    if len(df) >= 24:
        prev_day = df.iloc[-24:]
        result['pdh'] = float(prev_day['high'].max())
        result['pdl'] = float(prev_day['low'].min())

    # Recent session (last 6-12 candles)
    recent = df.iloc[-12:] if len(df) >= 12 else df
    result['london_high'] = float(recent['high'].max())
    result['london_low'] = float(recent['low'].min())

    # Asian session = first half of recent data
    half = len(recent) // 2
    if half > 0:
        asian = recent.iloc[:half]
        result['asian_high'] = float(asian['high'].max())
        result['asian_low'] = float(asian['low'].min())

    return result


def detect_liquidity_sweep(df, lookback=10):
    """
    Detect liquidity sweep (stop hunt):
    Price sweeps above BSL / below SSL then reverses back
    """
    result = {'detected': False, 'direction': '', 'swept_level': 0,
              'sweep_type': '', 'strength': 0, 'reversal_confirmed': False}

    if df is None or len(df) < lookback + 2:
        return result

    recent = df.iloc[-lookback-2:-1] if len(df) > lookback + 2 else df.iloc[:-1]
    current = df.iloc[-1]

    curr_high = float(current['high'])
    curr_low = float(current['low'])
    curr_close = float(current['close'])
    curr_open = float(current['open'])

    # Find recent high/low range
    recent_high = float(recent['high'].max())
    recent_low = float(recent['low'].min())

    # Check if current candle swept above recent high and reversed
    if curr_high > recent_high * 1.001:  # Swept above
        if curr_close < recent_high:  # Reversed back below
            result['detected'] = True
            result['direction'] = 'SELL'
            result['swept_level'] = recent_high
            result['sweep_type'] = 'BSL'
            result['strength'] = 3 if curr_close < curr_open else 2
            result['reversal_confirmed'] = curr_close < (recent_high + curr_low) / 2

    # Check if current candle swept below recent low and reversed
    elif curr_low < recent_low * 0.999:  # Swept below
        if curr_close > recent_low:  # Reversed back above
            result['detected'] = True
            result['direction'] = 'BUY'
            result['swept_level'] = recent_low
            result['sweep_type'] = 'SSL'
            result['strength'] = 3 if curr_close > curr_open else 2
            result['reversal_confirmed'] = curr_close > (recent_high + curr_low) / 2

    return result


def detect_inducement(df):
    """
    Detect inducement (fakeout to trap traders)
    Type 1: Reversal Trap - fake OB before reverse
    Type 2: Continuation Trap - fake breakout that fails
    """
    result = {'detected': False, 'type': '', 'level': 0,
              'direction': '', 'confidence': 0}

    if df is None or len(df) < 10:
        return result

    recent = df.iloc[-10:]
    current = df.iloc[-1]

    # Check for reversal trap: price breaks structure then reverses
    highs = recent['high'].values
    lows = recent['low'].values
    closes = recent['close'].values

    # Detect fake breakout (continuation trap)
    for i in range(3, len(recent) - 1):
        # Break above recent range
        if closes[i] > max(highs[i-3:i]) and closes[i+1] < closes[i]:
            result['detected'] = True
            result['type'] = 'CONTINUATION_TRAP'
            result['level'] = float(highs[i])
            result['direction'] = 'SELL'
            result['confidence'] = 2
            return result

        # Break below recent range
        if closes[i] < min(lows[i-3:i]) and closes[i+1] > closes[i]:
            result['detected'] = True
            result['type'] = 'CONTINUATION_TRAP'
            result['level'] = float(lows[i])
            result['direction'] = 'BUY'
            result['confidence'] = 2
            return result

    return result


def analyze_liquidity(df, current_price):
    """Wrapper: all liquidity analysis"""
    result = {'bsl_zones': [], 'ssl_zones': [], 'session_levels': {},
              'sweep': {}, 'inducement': {}, 'nearest_bsl': 0, 'nearest_ssl': 0,
              'has_recent_sweep': False, 'score': 0}

    if df is None or len(df) < 5:
        return result

    eq = find_equal_highs_lows(df)
    sess = find_session_levels(df)
    sweep = detect_liquidity_sweep(df)
    induce = detect_inducement(df)

    result['bsl_zones'] = eq['bsl_zones']
    result['ssl_zones'] = eq['ssl_zones']
    result['session_levels'] = sess
    result['sweep'] = sweep
    result['inducement'] = induce
    result['has_recent_sweep'] = sweep['detected']

    # Find nearest BSL/SSL to current price
    bsl_prices = [z['price'] for z in eq['bsl_zones']]
    ssl_prices = [z['price'] for z in eq['ssl_zones']]

    if bsl_prices:
        result['nearest_bsl'] = float(min(bsl_prices, key=lambda x: abs(x - current_price)))
    if ssl_prices:
        result['nearest_ssl'] = float(min(ssl_prices, key=lambda x: abs(x - current_price)))

    # Score: 0-25
    score = 0
    if eq['bsl_zones']:
        score += min(len(eq['bsl_zones']) * 3, 10)
    if eq['ssl_zones']:
        score += min(len(eq['ssl_zones']) * 3, 10)
    if sweep['detected']:
        score += sweep['strength'] * 4  # up to 12
    if induce['detected']:
        score += induce['confidence'] * 3

    result['score'] = min(score, 25)

    return result
