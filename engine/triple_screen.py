"""
SNIPER ULTRA — Elder Triple Screen + Impulse System
H4 trend -> H1 entry -> M15/M1 timing
"""
import numpy as np

def calc_ema(data, period):
    """Exponential Moving Average"""
    if len(data) < period:
        return None
    k = 2.0 / (period + 1)
    result = [float(data[0])]
    for i in range(1, len(data)):
        result.append(data[i] * k + result[-1] * (1 - k))
    return np.array(result)


def calc_macd(closes, fast=12, slow=26, signal=9):
    """Calculate MACD line, signal, and histogram"""
    if len(closes) < slow + signal:
        return None, None, None

    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)

    if ema_fast is None or ema_slow is None:
        return None, None, None

    min_len = min(len(ema_fast), len(ema_slow))
    macd_line = ema_fast[-min_len:] - ema_slow[-min_len:]
    
    signal_line = calc_ema(macd_line, signal)
    if signal_line is None:
        return None, None, None

    min_l = min(len(macd_line), len(signal_line))
    macd_line = macd_line[-min_l:]
    signal_line = signal_line[-min_l:]
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def detect_impulse(df, tf_name="H1"):
    """
    Elder Impulse System
    GREEN: EMA13 up + MACD-H up = LONG only
    RED: EMA13 down + MACD-H down = SHORT only
    BLUE: Divergence = reversal watch
    """
    result = {
        'signal': 'NEUTRAL', 'ema13_slope': 0, 'macd_h_slope': 0,
        'ema13': 0, 'macd_h': 0, 'tf': tf_name,
    }

    if df is None or len(df) < 30:
        return result

    closes = df['close'].values
    ema13 = calc_ema(closes, 13)

    if ema13 is None or len(ema13) < 5:
        return result

    ema_slope = ema13[-1] - ema13[-3]  # Slope over 3 bars
    result['ema13'] = round(float(ema13[-1]), 2)
    result['ema13_slope'] = round(float(ema_slope), 2)

    macd_l, macd_s, macd_h = calc_macd(closes)
    if macd_l is not None and len(macd_h) >= 3:
        h_slope = macd_h[-1] - macd_h[-3]
        result['macd_h'] = round(float(macd_h[-1]), 5)
        result['macd_h_slope'] = round(float(h_slope), 5)

        # Determine signal
        if ema_slope > 0 and h_slope > 0:
            result['signal'] = 'GREEN'
        elif ema_slope < 0 and h_slope < 0:
            result['signal'] = 'RED'
        elif (ema_slope > 0 and h_slope < 0) or (ema_slope < 0 and h_slope > 0):
            result['signal'] = 'BLUE'

    return result


def detect_triple_screen(htf_df, ltf_df, direction=None):
    """
    Elder Triple Screen System
    
    Screen 1 (HTF): Trend direction - trade ONLY in HTF direction
    Screen 2 (LTF): Find entry on pullback
    Screen 3 (M1): Timing
    
    Returns alignment status and recommendation
    """
    result = {
        'htf_trend': 'NEUTRAL', 'htf_impulse': {},
        'ltf_impulse': {}, 'alignment': 'NEUTRAL',
        'recommendation': 'WAIT', 'score': 0,
    }

    if htf_df is None or ltf_df is None:
        return result

    # Screen 1: HTF trend via structure + impulse
    from engine.smc import detect_market_structure
    htf_structure = detect_market_structure(htf_df)
    htf_impulse = detect_impulse(htf_df, "HTF")

    result['htf_trend'] = htf_structure['trend']
    result['htf_impulse'] = htf_impulse

    # Screen 2: LTF entry context
    ltf_structure = detect_market_structure(ltf_df)
    ltf_impulse = detect_impulse(ltf_df, "LTF")
    result['ltf_impulse'] = ltf_impulse

    # Screen 3: Alignment check
    htf_signal = htf_impulse['signal']
    ltf_signal = ltf_impulse['signal']

    # GREEN + GREEN = HIGH CONVICTION
    if htf_signal == 'GREEN' and ltf_signal == 'GREEN':
        result['alignment'] = 'FULL_BULL'
        result['recommendation'] = 'LONG'
    # RED + RED = HIGH CONVICTION
    elif htf_signal == 'RED' and ltf_signal == 'RED':
        result['alignment'] = 'FULL_BEAR'
        result['recommendation'] = 'SHORT'
    # Green HTF, Red LTF = pullback = good entry
    elif htf_signal == 'GREEN' and ltf_signal == 'RED':
        result['alignment'] = 'PULLBACK_BULL'
        result['recommendation'] = 'LONG_IF_CONFIRMED'
    # Red HTF, Green LTF = bounce only
    elif htf_signal == 'RED' and ltf_signal == 'GREEN':
        result['alignment'] = 'BOUNCE_ONLY'
        result['recommendation'] = 'SHORT_IF_CONFIRMED'
    # BLUE = transition
    elif htf_signal == 'BLUE' or ltf_signal == 'BLUE':
        result['alignment'] = 'TRANSITION'
        result['recommendation'] = 'CAUTION'

    # Score: 0-30
    alignment_scores = {
        'FULL_BULL': 30, 'FULL_BEAR': 30,
        'PULLBACK_BULL': 20, 'BOUNCE_ONLY': 15,
        'TRANSITION': 10, 'NEUTRAL': 0,
    }
    result['score'] = alignment_scores.get(result['alignment'], 0)

    return result


def calc_rsi(df, period=14):
    """Calculate RSI"""
    if df is None or len(df) < period + 1:
        return 50

    closes = df['close'].values
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(float(rsi), 1)


def analyze_triple_screen(data_dict, direction=None):
    """Wrapper: complete triple screen analysis from multi-TF data"""
    result = {
        'htf_structure': {}, 'htf_impulse': {}, 'ltf_impulse': {},
        'triple_screen': {}, 'rsi_htf': 50, 'rsi_ltf': 50,
        'score': 0,
    }

    if not data_dict:
        return result

    h1_df = data_dict.get('H1')
    m15_df = data_dict.get('M15')
    m1_df = data_dict.get('M1')

    ts = detect_triple_screen(h1_df, m15_df, direction)
    result['triple_screen'] = ts
    result['htf_impulse'] = ts['htf_impulse']
    result['ltf_impulse'] = ts['ltf_impulse']

    # RSI
    if h1_df is not None:
        result['rsi_htf'] = calc_rsi(h1_df)
        from engine.smc import detect_market_structure
        result['htf_structure'] = detect_market_structure(h1_df)
    if m1_df is not None:
        result['rsi_ltf'] = calc_rsi(m1_df)

    result['score'] = ts['score']

    return result
