"""
SNIPER ULTRA — Config
Exness XAUUSD | 1:2000 | $500
"""
from datetime import time, timezone

# ─── BROKER ───
SYMBOL = "XAUUSDm"
BROKER = "Exness"
SERVER = None           # Diisi manual: "Exness-MT5Trial14" atau server real
LOGIN = 0               # Diisi manual
PASSWORD = ""           # Diisi manual
MAGIC = 420690          # Unique bot ID

# ─── TIMEFRAMES ───
HTF = "H1"              # Higher timeframe (trend)
MTF = "M15"             # Mid timeframe (zones)
STF = "M5"              # Short timeframe (structure)
LTF = "M1"              # Entry timeframe

TF_MAP = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440, "W1": 10080
}

# ─── SESSION FILTER (UTC) ───
SESSION_ASIAN_START = time(0, 0)
SESSION_ASIAN_END = time(7, 59)
SESSION_LONDON_START = time(8, 0)
SESSION_LONDON_END = time(15, 59)
SESSION_NY_START = time(13, 0)
SESSION_NY_END = time(21, 59)

# ─── RISK MANAGEMENT ───
ACCOUNT_BALANCE = 500.0
RISK_PER_TRADE = 0.015       # 1.5% per trade ($7.50)
MAX_RISK_DAILY = 0.05        # 5% max daily loss ($25)
MAX_SPREAD_POINTS = 9999     # No spread filter — gas
MAX_OPEN_TRADES = 2
LOT_MIN = 0.01
LOT_MAX = 1.0
LOT_STEP = 0.01
LEVERAGE = 2000

# ─── CONFLUENCE SCORING ───
SCORE_MIN = 120              # Minimum score dari 200
SCORE_MAX = 200

# WEIGHTS
W_SND_ZONE = 30              # Supply & Demand di MPL
W_SMC_OB = 25                # Order Block dengan BOS
W_SMC_FVG = 20               # FVG mitgation
W_ELLIOT = 20                # Elliot Wave alignment
W_FIB_OTE = 20               # Fib di OTE zone (0.618-0.786)
W_LIQUIDITY_SWEEP = 25       # Liquidity sweep detected
W_CANDLE_PATTERN = 30        # Candlestick pattern (utama)
W_TRIPLE_SCREEN = 30         # Triple Screen alignment

# ─── 4-GATE ENTRY ───
CONFIRM_STRENGTH_MIN = 2     # Minimum 2/3
ENTRY_CONFIRMATION_WAIT = 5  # Max candles M1 untuk konfirmasi

# ─── SMART TRAILING (25% increment) ───
TRAILING_BE = 0.25           # 25% → Breakeven
TRAILING_ENABLED = True
TRAILING_ATR_PERIOD = 14
TRAILING_STAGES = [
    (0.25, 0.0, "BE"),       # 25% → Breakeven (0 ATR buffer)
    (0.50, 3.0, "50p"),      # 50% → 3x ATR
    (0.75, 2.5, "75p"),      # 75% → 2.5x ATR
    (1.00, 2.0, "100p"),     # 100% → 2x ATR
    (1.25, 1.5, "125p"),     # 125% → 1.5x ATR
    (1.50, 1.2, "150p"),     # 150% → 1.2x ATR
    (1.75, 1.0, "175p"),     # 175% → 1x ATR
    (2.00, 0.8, "200p"),     # 200% → 0.8x ATR
]

# ─── SL/TP ───
SL_ATR_MULT = 1.2            # SL = ATR * 1.2 (baseline)
TP_MIN_RR = 2.5              # Min RR 1:2.5
TP_IDEAL_RR = 2.8            # Ideal RR 1:2.8
SL_MIN = 2.0                 # $2 min SL distance
SL_MAX = 30.0                # $30 max SL distance
SR_ZONE_TOLERANCE = 0.5      # $0.50 buffer dari S&R level

# ─── SnD PARAMETERS ───
BASE_CANDLE_RATIO = 0.5      # Base candle range < 50% avg range
FRESH_ZONE_PREFERRED = True
MPL_LOOKBACK = 50            # Candles untuk cari MPL

# ─── SMC PARAMETERS ───
SWING_LOOKBACK = 3           # 3-bar swing detection
FVG_MIN_BODY = 0.3           # Min body ratio untuk valid FVG
FVG_EXPIRE_CANDLES = 50      # FVG expired setelah N candles
AMD_RANGE_THRESHOLD = 0.6    # Accumulation range < 60% prior range

# ─── LIQUIDITY ───
EQ_TOLERANCE = 0.002         # 0.2% tolerance untuk equal highs/lows
LIQ_LOOKBACK = 30            # Candles lookback

# ─── FIBONACCI ───
FIB_LEVELS_RETRACE = [0.236, 0.382, 0.500, 0.618, 0.764, 0.786]
FIB_LEVELS_EXTENSION = [0.0, 0.382, 0.618, 1.0, 1.272, 1.382, 1.618, 2.0, 2.618]
FIB_OTE_LOW = 0.618
FIB_OTE_HIGH = 0.786

# ─── SESSIONS ───
SESSION_WEIGHTS = {
    "ASIAN": 0.5,             # Low volatility
    "LONDON": 1.0,            # Active
    "NY": 1.2,                # Most active (overlap)
    "NY_LONDON": 1.5,         # Overlap = best
}

# ─── SELF-LEARNING ───
LEARNING_DB = "trades.db"
LEARNING_ANALYZE_EVERY = 20  # Analyze after N trades
CIRCUIT_BREAKER_LOSSES = 3   # Stop after 3 consecutive losses
CIRCUIT_BREAKER_DAILY = 5    # Stop after 5 daily losses
DAILY_MAX_LOSS = 25.0        # $25 max daily loss
