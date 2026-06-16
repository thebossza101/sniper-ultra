"""
SNIPER ULTRA — SMC Engine (BOS/CHoCH, Order Blocks, FVG, AMD, Market Structure)
"""
import numpy as np

def find_swing_points(df, lookback=3):
    """Find all swing highs (SH) and swing lows (SL)"""
    highs, lows = [], []
    if df is None or len(df) < lookback * 2 + 1:
        return highs, lows

    h = df['high'].values
    l = df['low'].values
    for i in range(lookback, len(df) - lookback):
        if all(h[i] > h[j] for j in range(i-lookback, i+lookback+1) if j != i):
            highs.append((i, float(h[i])))
        if all(l[i] < l[j] for j in range(i-lookback, i+lookback+1) if j != i):
            lows.append((i, float(l[i])))
    return highs, lows


def detect_bos_choch(df, lookback=3):
    """
    Detect Break of Structure (BOS) and Change of Character (CHoCH)
    
    Bullish BOS: close above last swing high
    Bearish BOS: close below last swing low
    CHoCH: first break that signals trend change
    """
    result = {
        'bos_detected': False, 'bos_direction': '', 'bos_level': 0,
        'choch_detected': False, 'choch_direction': '', 'choch_level': 0,
        'bos_count_bull': 0, 'bos_count_bear': 0,
    }

    if df is None or len(df) < 10:
        return result

    highs, lows = find_swing_points(df, lookback)
    if len(highs) < 2 and len(lows) < 2:
        return result

    current_close = float(df.iloc[-1]['close'])
    current_high = float(df.iloc[-1]['high'])
    current_low = float(df.iloc[-1]['low'])

    # Check BOS: current close beyond last swing point
    if highs:
        last_sh = highs[-1][1]
        if current_close > last_sh:
            result['bos_detected'] = True
            result['bos_direction'] = 'BULL'
            result['bos_level'] = last_sh
            result['bos_count_bull'] += 1

    if lows:
        last_sl = lows[-1][1]
        if current_close < last_sl:
            result['bos_detected'] = True
            result['bos_direction'] = 'BEAR'
            result['bos_level'] = last_sl
            result['bos_count_bear'] += 1

    # Count historical BOS
    for i in range(1, len(highs)):
        if highs[i][1] > highs[i-1][1]:
            result['bos_count_bull'] += 1
    for i in range(1, len(lows)):
        if lows[i][1] < lows[i-1][1]:
            result['bos_count_bear'] += 1

    # CHoCH: first break in opposite direction after trend
    if len(highs) >= 2 and len(lows) >= 2:
        last_high_i, last_high = highs[-1]
        last_low_i, last_low = lows[-1]

        # Bullish CHoCH: price was making lower lows, then breaks above last swing high
        recent_lows = [l[1] for l in lows[-3:]] if len(lows) >= 3 else [l[1] for l in lows]
        if len(recent_lows) >= 2 and recent_lows[-1] > recent_lows[-2]:
            # Was bearish (making lower lows), now higher low = potential CHoCH
            if result['bos_direction'] == 'BULL':
                result['choch_detected'] = True
                result['choch_direction'] = 'BULL'
                result['choch_level'] = last_low

        # Bearish CHoCH
        recent_highs = [h[1] for h in highs[-3:]] if len(highs) >= 3 else [h[1] for h in highs]
        if len(recent_highs) >= 2 and recent_highs[-1] < recent_highs[-2]:
            if result['bos_direction'] == 'BEAR':
                result['choch_detected'] = True
                result['choch_direction'] = 'BEAR'
                result['choch_level'] = last_high

    return result


def detect_order_blocks(df, lookback=50):
    """
    Detect Order Blocks: last opposite candle before impulsive BOS move
    SYARAT MUTLAK: OB harus menyebabkan BOS!
    
    Bullish OB: Last BEARISH candle before bullish BOS
    Bearish OB: Last BULLISH candle before bearish BOS
    """
    result = {'bullish_obs': [], 'bearish_obs': []}

    if df is None or len(df) < 10:
        return result

    closes = df['close'].values
    opens = df['open'].values
    highs = df['high'].values
    lows = df['low'].values

    avg_body = np.mean(np.abs(closes - opens))

    for i in range(3, min(lookback, len(df) - 3)):
        # Look for impulse move after candle i
        body_i = abs(closes[i] - opens[i])
        if body_i < avg_body * 0.5:
            continue  # Skip small candles

        # Check next 2-3 candles for impulse
        for j in range(i+1, min(i+4, len(df))):
            impulse_range = abs(closes[j] - opens[i])

            # Need impulse > 2x avg body to be significant
            if impulse_range < avg_body * 2:
                continue

            # Bullish OB: bearish candle at i, followed by bullish impulse
            if closes[i] < opens[i] and closes[j] > highs[i]:
                # Check BOS occurred
                swing_high = max(highs[max(0,i-3):i+1])
                if closes[j] > swing_high * 1.001:  # BOS confirmed
                    ob = {
                        'type': 'BULLISH_OB',
                        'direction': 'BUY',
                        'top': float(highs[i]),
                        'bottom': float(lows[i]),
                        'closes[i]': float(closes[i]),
                        'opens[i]': float(opens[i]),
                        'index': int(i),
                        'bos_price': float(closes[j]),
                        'bos_index': int(j),
                        'fresh': True,
                    }

                    # Check freshness (has this OB been mitigated yet?)
                    for k in range(i, min(i+15, len(df) - 1)):
                        if lows[k] <= lows[i]:
                            ob['fresh'] = False
                            break

                    result['bullish_obs'].append(ob)
                break

            # Bearish OB: bullish candle at i, followed by bearish impulse
            elif closes[i] > opens[i] and closes[j] < lows[i]:
                swing_low = min(lows[max(0,i-3):i+1])
                if closes[j] < swing_low * 0.999:
                    ob = {
                        'type': 'BEARISH_OB',
                        'direction': 'SELL',
                        'top': float(highs[i]),
                        'bottom': float(lows[i]),
                        'index': int(i),
                        'bos_price': float(closes[j]),
                        'fresh': True,
                    }
                    for k in range(i, min(i+15, len(df) - 1)):
                        if highs[k] >= highs[i]:
                            ob['fresh'] = False
                            break
                    result['bearish_obs'].append(ob)
                break

    # Sort by recency (most recent first)
    result['bullish_obs'].sort(key=lambda x: x['index'], reverse=True)
    result['bearish_obs'].sort(key=lambda x: x['index'], reverse=True)

    return result


def detect_fvg(df, lookback=50):
    """
    Fair Value Gap detection (imbalance)
    Bullish FVG: gap between candle[i-2].high and candle[i].low
    Bearish FVG: gap between candle[i].high and candle[i-2].low
    
    Tracks mitigation status
    """
    result = {'bullish_fvgs': [], 'bearish_fvgs': []}

    if df is None or len(df) < 5:
        return result

    highs = df['high'].values
    lows = df['low'].values

    for i in range(2, min(lookback, len(df) - 1)):
        # Bullish FVG: candle[i-2].high < candle[i].low (gap up)
        if highs[i-2] < lows[i]:
            gap = lows[i] - highs[i-2]
            if gap > 0:
                fvg = {
                    'type': 'BULLISH_FVG',
                    'direction': 'BUY',
                    'high': float(highs[i-2]),
                    'low': float(lows[i]),
                    'gap': float(gap),
                    'index': int(i),
                    'mitigated': False,
                    'mitigated_pct': 0.0,
                }

                # Check mitigation
                for j in range(i, min(i + 50, len(df))):
                    if lows[j] <= highs[i-2]:
                        fvg['mitigated'] = True
                        fvg['mitigated_pct'] = 100.0
                        break
                    elif highs[i-2] < df.iloc[j]['close'] < lows[i]:
                        mit = (lows[i] - df.iloc[j]['close']) / gap
                        fvg['mitigated_pct'] = round(float(mit * 100), 1)

                result['bullish_fvgs'].append(fvg)

        # Bearish FVG: candle[i].high < candle[i-2].low (gap down)
        elif highs[i] < lows[i-2]:
            gap = lows[i-2] - highs[i]
            if gap > 0:
                fvg = {
                    'type': 'BEARISH_FVG',
                    'direction': 'SELL',
                    'high': float(highs[i]),
                    'low': float(lows[i-2]),
                    'gap': float(gap),
                    'index': int(i),
                    'mitigated': False,
                    'mitigated_pct': 0.0,
                }

                for j in range(i, min(i + 50, len(df))):
                    if highs[j] >= lows[i-2]:
                        fvg['mitigated'] = True
                        fvg['mitigated_pct'] = 100.0
                        break
                    elif lows[i-2] > df.iloc[j]['close'] > highs[i]:
                        mit = (df.iloc[j]['close'] - highs[i]) / gap
                        fvg['mitigated_pct'] = round(float(mit * 100), 1)

                result['bearish_fvgs'].append(fvg)

    # Sort by gap size (largest first)
    result['bullish_fvgs'].sort(key=lambda x: x['gap'], reverse=True)
    result['bearish_fvgs'].sort(key=lambda x: x['gap'], reverse=True)

    return result


def detect_amd_cycle(df):
    """
    Detect AMD (Accumulation, Manipulation, Distribution) cycle
    
    Accumulation: tight range, low volatility
    Manipulation: fake breakout opposite direction
    Distribution: trending move in true direction
    """
    result = {'phase': 'UNKNOWN', 'accumulation': False, 'manipulation': False,
              'distribution': False, 'range_high': 0, 'range_low': 0}

    if df is None or len(df) < 20:
        return result

    # Check last 8-12 candles for range
    recent = df.iloc[-12:] if len(df) >= 12 else df
    older = df.iloc[-24:-12] if len(df) >= 24 else df.iloc[:len(df)//2]

    recent_range = float(recent['high'].max() - recent['low'].min())
    older_range = float(older['high'].max() - older['low'].min()) if len(older) > 0 else recent_range

    avg_body_recent = float(np.mean(recent['close'] - recent['open']))
    avg_body_older = float(np.mean(np.abs(older['close'] - older['open']))) if len(older) > 0 else avg_body_recent

    # Accumulation: range tightening, lower volatility
    if older_range > 0 and recent_range < older_range * 0.6:
        result['accumulation'] = True
        result['phase'] = 'ACCUMULATION'
        result['range_high'] = float(recent['high'].max())
        result['range_low'] = float(recent['low'].min())

    # Manipulation: price broke accumulation range then reversed
    if result['accumulation']:
        current = df.iloc[-1]
        curr_close = float(current['close'])
        if curr_close < result['range_low'] or curr_close > result['range_high']:
            # Broke out of range
            if abs(curr_close - result['range_low']) < recent_range * 0.3:
                # Broke below - potential bullish manipulation
                result['manipulation'] = True
                result['phase'] = 'MANIPULATION'

    # Distribution: trending with momentum after manipulation
    if result['manipulation'] or (recent_range > older_range * 1.5 and avg_body_recent > avg_body_older * 1.3):
        # Check if moving with momentum
        direction = 0
        for i in range(1, len(recent)):
            if recent.iloc[i]['close'] > recent.iloc[i-1]['close']:
                direction += 1
            else:
                direction -= 1
        if abs(direction) >= len(recent) * 0.5:  # 50%+ in same direction
            result['distribution'] = True
            result['phase'] = 'DISTRIBUTION'

    return result


def detect_market_structure(df, lookback=30):
    """
    Determine market structure trend and sequence
    
    Bullish: HH + HL (Higher High + Higher Low)
    Bearish: LH + LL (Lower High + Lower Low)
    Neutral: Ranging
    """
    result = {'trend': 'NEUTRAL', 'sequence': '', 'hh_count': 0, 'll_count': 0,
              'last_high': 0, 'last_low': 0}

    if df is None or len(df) < 10:
        return result

    highs, lows = find_swing_points(df, lookback=2)

    if len(highs) < 2 or len(lows) < 2:
        return result

    # Analyze sequence
    hh_count = sum(1 for i in range(1, len(highs)) if highs[i][1] > highs[i-1][1])
    ll_count = sum(1 for i in range(1, len(lows)) if lows[i][1] < lows[i-1][1])

    # Check last 3 swings for current structure
    last_highs = [h[1] for h in highs[-3:]] if len(highs) >= 3 else [h[1] for h in highs]
    last_lows = [l[1] for l in lows[-3:]] if len(lows) >= 3 else [l[1] for l in lows]

    seq = []
    # Build sequence interleaving highs and lows
    combined = []
    for h in highs[-5:]:
        combined.append(('H', h[0], h[1]))
    for l in lows[-5:]:
        combined.append(('L', l[0], l[1]))
    combined.sort(key=lambda x: x[1])

    seq_str = ' '.join([f"{s[0]}={s[2]:.1f}" for s in combined[-6:]])

    # Determine trend
    if len(last_highs) >= 2 and len(last_lows) >= 2:
        if last_highs[-1] > last_highs[-2] and last_lows[-1] > last_lows[-2]:
            result['trend'] = 'BULL'
        elif last_highs[-1] < last_highs[-2] and last_lows[-1] < last_lows[-2]:
            result['trend'] = 'BEAR'

    result['sequence'] = seq_str
    result['hh_count'] = hh_count
    result['ll_count'] = ll_count
    result['last_high'] = float(highs[-1][1]) if highs else 0
    result['last_low'] = float(lows[-1][1]) if lows else 0

    return result


def analyze_smc(df, current_price):
    """Wrapper: complete SMC analysis"""
    result = {
        'structure': {}, 'bos_choch': {}, 'bullish_obs': [], 'bearish_obs': [],
        'bullish_fvgs': [], 'bearish_fvgs': [], 'amd': {},
        'in_bullish_ob': False, 'in_bearish_ob': False,
        'in_bullish_fvg': False, 'in_bearish_fvg': False,
        'score': 0,
    }

    if df is None or len(df) < 10:
        return result

    structure = detect_market_structure(df)
    bos = detect_bos_choch(df)
    obs = detect_order_blocks(df)
    fvgs = detect_fvg(df)
    amd = detect_amd_cycle(df)

    result['structure'] = structure
    result['bos_choch'] = bos
    result['bullish_obs'] = obs['bullish_obs']
    result['bearish_obs'] = obs['bearish_obs']
    result['bullish_fvgs'] = fvgs['bullish_fvgs']
    result['bearish_fvgs'] = fvgs['bearish_fvgs']
    result['amd'] = amd

    # Check if price is in OB
    for ob in obs['bullish_obs']:
        if ob['bottom'] <= current_price <= ob['top']:
            result['in_bullish_ob'] = True
            break
    for ob in obs['bearish_obs']:
        if ob['bottom'] <= current_price <= ob['top']:
            result['in_bearish_ob'] = True
            break

    # Check if price is in FVG (unfilled)
    for fvg in fvgs['bullish_fvgs']:
        if not fvg['mitigated'] and fvg['high'] <= current_price <= fvg['low']:
            result['in_bullish_fvg'] = True
            break
    for fvg in fvgs['bearish_fvgs']:
        if not fvg['mitigated'] and fvg['high'] <= current_price <= fvg['low']:
            result['in_bearish_fvg'] = True
            break

    # Score: 0-45
    score = 0

    # Structure score
    if structure['trend'] == 'BULL':
        score += 5
    elif structure['trend'] == 'BEAR':
        score += 5

    # BOS/CHoCH score
    if bos['bos_detected']:
        score += 10
    if bos['choch_detected']:
        score += 8

    # OB score
    fresh_bull_obs = sum(1 for ob in obs['bullish_obs'] if ob.get('fresh', True))
    fresh_bear_obs = sum(1 for ob in obs['bearish_obs'] if ob.get('fresh', True))
    score += min(fresh_bull_obs * 3, 8)
    score += min(fresh_bear_obs * 3, 8)

    # FVG score
    unfilled_bull_fvg = sum(1 for f in fvgs['bullish_fvgs'] if not f['mitigated'])
    unfilled_bear_fvg = sum(1 for f in fvgs['bearish_fvgs'] if not f['mitigated'])
    score += min(unfilled_bull_fvg * 3, 5)
    score += min(unfilled_bear_fvg * 3, 5)

    # AMD score
    if amd['distribution']:
        score += 10
    elif amd['manipulation']:
        score += 7
    elif amd['accumulation']:
        score += 3

    # In zone bonus
    if result['in_bullish_ob'] or result['in_bullish_fvg']:
        score += 5
    if result['in_bearish_ob'] or result['in_bearish_fvg']:
        score += 5

    result['score'] = min(score, 45)

    return result
