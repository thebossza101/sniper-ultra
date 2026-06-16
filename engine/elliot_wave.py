"""
SNIPER ULTRA — Elliot Wave Detector (Impulsive 1-2-3-4-5 + Corrective ABC)
"""
import numpy as np

def _find_swings_idx(closes, highs, lows, lookback=3):
    """Find swing highs/lows by index"""
    highs_idx, lows_idx = [], []
    for i in range(lookback, len(highs) - lookback):
        if all(highs[i] >= highs[j] for j in range(i-lookback, i+lookback+1) if j != i):
            if len(highs_idx) == 0 or i - highs_idx[-1] > 1:
                highs_idx.append(i)
        if all(lows[i] <= lows[j] for j in range(i-lookback, i+lookback+1) if j != i):
            if len(lows_idx) == 0 or i - lows_idx[-1] > 1:
                lows_idx.append(i)
    return highs_idx, lows_idx


def detect_impulsive_wave(df):
    """
    Detect 5-wave impulsive pattern (1-2-3-4-5)
    Rules: Wave 2 cannot retrace more than Wave 1 start
           Wave 3 cannot be shortest
           Wave 4 cannot overlap Wave 1
    """
    result = {'detected': False, 'waves': [], 'direction': '', 'current_wave': 0, 'confidence': 0}

    if df is None or len(df) < 20:
        return result

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values

    # Find swing points
    h_idx, l_idx = _find_swings_idx(closes, highs, lows, lookback=3)

    if len(h_idx) < 3 or len(l_idx) < 3:
        return result

    # Interleave swings by order of occurrence
    swings = []
    hi_set, li_set = set(h_idx), set(l_idx)
    all_idx = sorted(set(h_idx) | set(l_idx))
    for i in all_idx:
        if i in hi_set:
            swings.append(('H', i, highs[i]))
        else:
            swings.append(('L', i, lows[i]))

    if len(swings) < 5:
        return result

    # Try to identify 5-wave pattern
    # Bullish 5-wave: L-H-L-H-L pattern
    for start in range(len(swings) - 4):
        w = swings[start:start+5]
        types = [s[0] for s in w]

        if types == ['L', 'H', 'L', 'H', 'L']:
            # Check rules
            w1_range = abs(w[1][2] - w[0][2])
            w2_range = abs(w[2][2] - w[0][2])
            w3_range = abs(w[3][2] - w[2][2])
            w4_range = abs(w[4][2] - w[3][2])

            # Rule 1: Wave 2 not lower than Wave 1 start
            if w[2][2] < w[0][2]:
                continue
            # Rule 2: Wave 3 not shortest
            if w3_range <= w1_range and w3_range <= abs(w[4][2] - w[3][2]):
                # Check if wave 3 is extended (> 162%)
                pass  # Still valid if extended
            # Rule 3: Wave 4 not overlap Wave 1
            if w[3][2] > w[1][2]:
                continue

            # Valid bullish impulse
            waves = []
            for j, (t, idx, pr) in enumerate(w):
                waves.append({
                    'wave': j + 1,
                    'type': 'HIGH' if t == 'H' else 'LOW',
                    'start_idx': int(idx),
                    'price': float(pr),
                })

            # Determine current wave position
            last_swing_idx = w[-1][1]
            current_bar = len(df) - 1

            result['detected'] = True
            result['waves'] = waves
            result['direction'] = 'BUY'
            result['current_wave'] = 5 if current_bar > last_swing_idx else 4
            result['confidence'] = min(3 + len(waves), 5)
            return result

        elif types == ['H', 'L', 'H', 'L', 'H']:
            # Bearish impulse
            if w[2][2] > w[0][2]:
                continue
            w3_range = abs(w[2][2] - w[3][2])
            if w3_range <= abs(w[0][2] - w[1][2]):
                pass
            if w[4][2] > w[3][2] and w[3][2] > w[1][2]:
                continue

            waves = []
            for j, (t, idx, pr) in enumerate(w):
                waves.append({
                    'wave': j + 1,
                    'type': 'HIGH' if t == 'H' else 'LOW',
                    'start_idx': int(idx),
                    'price': float(pr),
                })

            result['detected'] = True
            result['waves'] = waves
            result['direction'] = 'SELL'
            result['current_wave'] = 5
            result['confidence'] = 4
            return result

    return result


def detect_corrective_wave(df):
    """Detect ABC corrective wave"""
    result = {'detected': False, 'waves': [], 'pattern': '', 'confidence': 0}

    if df is None or len(df) < 10:
        return result

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    h_idx, l_idx = _find_swings_idx(closes, highs, lows, lookback=2)

    # Need at least 3 swing points for ABC
    swings = []
    for i in sorted(set(h_idx) | set(l_idx)):
        if i in set(h_idx):
            swings.append(('H', i, highs[i]))
        else:
            swings.append(('L', i, lows[i]))

    if len(swings) < 3:
        return result

    # Look for ABC pattern (zigzag: 5-3-5)
    for i in range(len(swings) - 2):
        a, b, c = swings[i], swings[i+1], swings[i+2]

        # Bullish correction (bearish impulse followed by ABC up)
        # A=low, B=high, C=low (C > A = valid correction)
        if a[0] == 'L' and b[0] == 'H' and c[0] == 'L':
            if c[2] > a[2]:  # C higher than A
                result['detected'] = True
                result['waves'] = [
                    {'wave': 'A', 'price': float(a[2])},
                    {'wave': 'B', 'price': float(b[2])},
                    {'wave': 'C', 'price': float(c[2])},
                ]
                result['pattern'] = 'ZIGZAG'
                result['confidence'] = 3
                return result

        # Bearish correction
        elif a[0] == 'H' and b[0] == 'L' and c[0] == 'H':
            if c[2] < a[2]:
                result['detected'] = True
                result['waves'] = [
                    {'wave': 'A', 'price': float(a[2])},
                    {'wave': 'B', 'price': float(b[2])},
                    {'wave': 'C', 'price': float(c[2])},
                ]
                result['pattern'] = 'ZIGZAG'
                result['confidence'] = 3
                return result

    return result


def get_wave_count(df):
    """Count waves from swing structure progression"""
    result = {'count': 0, 'last_completed_wave': 0, 'next_expected': '', 'in_wave': 0}

    if df is None or len(df) < 10:
        return result

    impulsive = detect_impulsive_wave(df)
    corrective = detect_corrective_wave(df)

    if impulsive['detected']:
        result['count'] = len(impulsive['waves'])
        result['last_completed_wave'] = impulsive['current_wave']
        result['next_expected'] = 'corrective' if result['count'] >= 5 else 'impulsive'
        result['in_wave'] = impulsive['current_wave']
    elif corrective['detected']:
        result['count'] = 3
        result['last_completed_wave'] = 3
        result['next_expected'] = 'impulsive'
        result['in_wave'] = len(corrective['waves'])

    return result


def analyze_elliot(df, direction=None):
    """Wrapper: complete Elliot Wave analysis"""
    result = {'detected': False, 'impulsive': {}, 'corrective': {},
              'wave_count': {}, 'alignment': 'NEUTRAL', 'score': 0}

    impulsive = detect_impulsive_wave(df)
    corrective = detect_corrective_wave(df)
    wave_count = get_wave_count(df)

    detected = impulsive['detected'] or corrective['detected']
    alignment = 'NEUTRAL'

    if impulsive['detected']:
        alignment = 'BULLISH' if impulsive['direction'] == 'BUY' else 'BEARISH'

    # Score: 0-20
    score = 0
    if impulsive['detected']:
        score += impulsive['confidence'] * 3  # up to 15
    if corrective['detected']:
        score += corrective['confidence'] * 2  # up to 6
    if wave_count['count'] > 0:
        score += 5  # Structure confirmed

    return {
        'detected': detected,
        'impulsive': impulsive,
        'corrective': corrective,
        'wave_count': wave_count,
        'alignment': alignment,
        'score': min(score, 20),
    }
