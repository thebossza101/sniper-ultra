"""
SNIPER ULTRA — Supply & Demand Engine (RBR, RBD, DBR, DBD, MPL, Compression, Fakeout)
"""
import numpy as np

def _avg_range(df, period=14):
    """Average candle range"""
    if df is None or len(df) < period:
        return 0
    ranges = (df['high'] - df['low']).values[-period:]
    return float(np.mean(ranges))


def detect_snd_zones(df, lookback=30):
    """
    Detect Supply & Demand zones (RBR, RBD, DBR, DBD)
    
    Returns categorized zones with MPL marking
    """
    result = {'zones': [], 'buy_zones': [], 'sell_zones': [],
              'mpl': None, 'compression': False, 'fakeout': False}

    if df is None or len(df) < 10:
        return result

    avg_rng = _avg_range(df)
    if avg_rng == 0:
        return result

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    opens = df['open'].values

    # Scan for base/rally/drop patterns
    for i in range(2, min(lookback, len(df) - 2)):
        # Base = consolidation (range < 50% avg range)
        c_range = highs[i] - lows[i]
        if c_range > avg_rng * 0.5:
            continue

        # Check pattern context (look 3 candles ahead)
        if i + 3 >= len(df):
            break

        after_high = max(highs[i+1:i+4])
        after_low = min(lows[i+1:i+4])
        before_high = max(highs[max(0,i-3):i])
        before_low = min(lows[max(0,i-3):i])

        # RBR (Rally Base Rally) - BUY zone
        if before_high > highs[i] and after_high > highs[i]:
            zone = {
                'type': 'RBR',
                'direction': 'BUY',
                'top': float(highs[i]),
                'bottom': float(lows[i]),
                'mid': float((highs[i] + lows[i]) / 2),
                'fresh': True,
                'index': int(i),
            }
            result['zones'].append(zone)
            result['buy_zones'].append(zone)

        # DBD (Drop Base Drop) - SELL zone
        elif before_low < lows[i] and after_low < lows[i]:
            zone = {
                'type': 'DBD',
                'direction': 'SELL',
                'top': float(highs[i]),
                'bottom': float(lows[i]),
                'mid': float((highs[i] + lows[i]) / 2),
                'fresh': True,
                'index': int(i),
            }
            result['zones'].append(zone)
            result['sell_zones'].append(zone)

        # RBD (Rally Base Drop) - SELL reversal
        elif before_high > highs[i] and after_low < lows[i]:
            zone = {
                'type': 'RBD',
                'direction': 'SELL',
                'top': float(highs[i]),
                'bottom': float(lows[i]),
                'mid': float((highs[i] + lows[i]) / 2),
                'fresh': True,
                'index': int(i),
            }
            result['zones'].append(zone)
            result['sell_zones'].append(zone)

        # DBR (Drop Base Rally) - BUY reversal
        elif before_low < lows[i] and after_high > highs[i]:
            zone = {
                'type': 'DBR',
                'direction': 'BUY',
                'top': float(highs[i]),
                'bottom': float(lows[i]),
                'mid': float((highs[i] + lows[i]) / 2),
                'fresh': True,
                'index': int(i),
            }
            result['zones'].append(zone)
            result['buy_zones'].append(zone)

    # Check Freshness (price sudah pernah ke zone atau belum?)
    current_price = float(df.iloc[-1]['close'])
    for zone in result['zones']:
        zone['distance'] = abs(current_price - zone['mid'])
        # If recent price has touched this zone, it's not fresh
        for j in range(max(0, len(df) - 20), len(df)):
            if zone['bottom'] <= df.iloc[j]['high'] and zone['top'] >= df.iloc[j]['low']:
                zone['fresh'] = False
                break

    # Sort by distance
    result['zones'].sort(key=lambda x: x['distance'])
    result['buy_zones'].sort(key=lambda x: x['distance'])
    result['sell_zones'].sort(key=lambda x: x['distance'])

    # Detect compression
    result['compression'] = _detect_compression(df, avg_rng)
    result['fakeout'] = _detect_fakeout(df)

    return result


def _detect_compression(df, avg_rng):
    """Detect compression (tightening range = impending breakout)"""
    if len(df) < 10:
        return False
    recent_range = (df['high'].iloc[-5:].max() - df['low'].iloc[-5:].min())
    return recent_range < avg_rng * 0.6


def _detect_fakeout(df):
    """Detect fakeout (false breakout)"""
    if len(df) < 10:
        return False
    recent = df.iloc[-6:-1]
    current = df.iloc[-1]
    
    # Check if price broke a level then reversed
    recent_high = recent['high'].max()
    recent_low = recent['low'].min()

    # Broke above high but closed back inside
    if current['high'] > recent_high and current['close'] < recent_high:
        return True
    # Broke below low but closed back inside
    if current['low'] < recent_low and current['close'] > recent_low:
        return True

    return False


def detect_mpl(df, lookback=50):
    """
    Maximum Pain Level — long red marubozu breaking support (for SELL)
    or long blue marubozu breaking resistance (for BUY)
    """
    result = {'mpl_sell': 0, 'mpl_buy': 0, 'detected': False}

    if df is None or len(df) < 5:
        return result

    for i in range(1, min(lookback, len(df))):
        c = df.iloc[i]
        prev = df.iloc[i-1]
        body = abs(c['close'] - c['open'])
        rng = c['high'] - c['low']
        if rng == 0:
            continue
        body_ratio = body / rng

        # Long marubozu (body > 70% of range)
        if body_ratio < 0.7:
            continue

        # Bearish marubozu breaking prev low = MPL for SELL
        if c['close'] < c['open'] and c['close'] < prev['low']:
            result['mpl_sell'] = float(c['close'])
            result['detected'] = True

        # Bullish marubozu breaking prev high = MPL for BUY
        elif c['close'] > c['open'] and c['close'] > prev['high']:
            result['mpl_buy'] = float(c['close'])
            result['detected'] = True

    return result


def detect_quasimodo(df):
    """Quasimodo pattern (over & under): like H&S but with LL/LH after neckline"""
    result = {'detected': False, 'type': '', 'direction': '', 'entry': 0, 'sl': 0, 'tp': 0}
    
    if df is None or len(df) < 20:
        return result

    highs = df['high'].values
    lows = df['low'].values
    
    # Find swing points
    swing_highs, swing_lows = [], []
    for i in range(2, len(df) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            swing_highs.append((i, highs[i]))
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            swing_lows.append((i, lows[i]))

    if len(swing_highs) < 3 or len(swing_lows) < 3:
        return result

    # Bearish Quasimodo: higher high (over), then lower low (under)
    h1 = swing_highs[-3][1]
    h2 = swing_highs[-2][1]
    h3 = swing_highs[-1][1]
    l1 = swing_lows[-3][1]
    l2 = swing_lows[-2][1]
    l3 = swing_lows[-1][1]

    if h2 > h1 and h2 > h3:  # Higher high
        if l3 < l2 and l3 < l1:  # Lower low after
            result['detected'] = True
            result['type'] = 'QUASIMODO'
            result['direction'] = 'SELL'
            result['entry'] = float(l3)  # Sell below the break
            result['sl'] = float(h2)
            result['tp'] = float(l3 - (h2 - l3))
            
    return result


def analyze_snd(df, current_price):
    """Wrapper: complete Supply & Demand analysis"""
    result = {'zones': [], 'buy_zones': [], 'sell_zones': [],
              'mpl': {}, 'compression': False, 'fakeout': False,
              'quasimodo': {}, 'zone_status': 'NO_ZONE',
              'nearest_buy_zone': 0, 'nearest_sell_zone': 0,
              'score': 0, 'in_zone': False}

    zones = detect_snd_zones(df)
    mpl = detect_mpl(df)
    qm = detect_quasimodo(df)
    
    result['zones'] = zones['zones']
    result['buy_zones'] = zones['buy_zones']
    result['sell_zones'] = zones['sell_zones']
    result['mpl'] = mpl
    result['compression'] = zones['compression']
    result['fakeout'] = zones['fakeout']
    result['quasimodo'] = qm

    # Determine zone status
    nearest_buy = None
    nearest_sell = None
    min_buy_dist = 999
    min_sell_dist = 999

    for z in zones['buy_zones']:
        if z['fresh']:
            d = z['distance']
            if d < min_buy_dist:
                min_buy_dist = d
                nearest_buy = z

    for z in zones['sell_zones']:
        if z['fresh']:
            d = z['distance']
            if d < min_sell_dist:
                min_sell_dist = d
                nearest_sell = z

    # Check if price is inside a zone
    for z in zones['zones']:
        if z['bottom'] <= current_price <= z['top']:
            result['in_zone'] = True
            if z['direction'] == 'BUY':
                result['zone_status'] = 'BUY_ZONE'
            else:
                result['zone_status'] = 'SELL_ZONE'
            break

    # Only mark CONFLICT if both buy and sell zones are very close (< 1 ATR apart)
    if nearest_buy and nearest_sell:
        if abs(nearest_buy['mid'] - nearest_sell['mid']) < 3.0:  # ~$3 for XAUUSD
            if result['zone_status'] != 'NO_ZONE':
                result['zone_status'] = 'CONFLICT'

    if nearest_buy:
        result['nearest_buy_zone'] = nearest_buy['mid']
    if nearest_sell:
        result['nearest_sell_zone'] = nearest_sell['mid']

    # Score: 0-30
    score = 0
    fresh_zones = sum(1 for z in zones['zones'] if z['fresh'])
    score += min(fresh_zones * 3, 10)  # Up to 10 for zone count
    if result['in_zone']:
        score += 10  # In zone bonus
    if result['zone_status'] == 'BUY_ZONE' or result['zone_status'] == 'SELL_ZONE':
        score += 5  # Clear direction
    if zones['fakeout']:
        score += 5  # Potential reversal
    if mpl['detected']:
        score += 5  # MPL detected

    result['score'] = min(score, 30)

    return result
