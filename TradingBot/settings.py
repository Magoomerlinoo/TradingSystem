import MetaTrader5 as mt5
DEFAULT_BALANCE = 4_000
RISK_PERCENT = 0.01
MANUAL_POSITION_MULTIPLIER = 1.0
# TELEGRAM SETTINGS
TELEGRAM_TOKEN = "placeholder"
TELEGRAM_CHAT_ID = "placeholder"
ATR_MULTIPLIER = {
    "ranging":       0.3,
    "trending_up":   0.5,
    "trending_down": 0.5,
    "volatile":      0.8,
}
ATR_PERIOD = 7
MIN_LOT_SIZE = 0.05
LOOKBACK = 50
DEBUG_BUILD = True     # mettilo a False quando non ti serve più
ENABLE_TRAILING_STOPS = True
ENABLE_PARTIAL_TP = True
ENABLE_BREAK_EVEN = True
ENABLE_DAILY_LOSS_LIMIT = True
ENABLE_COMBO_CONFIDENCE_BOOST = True
ALERTS_ENABLED = True
DYNAMIC_RR_ENABLED = True
DEFAULT_RR_RATIO = 1.5
STRATEGY_MODE = "normal"
THRESHOLD_PERCENTS = {
    "normal": {
        "ranging":       0.35,   # soglia ≈ 35 % dell’ATR
        "trending_up":   0.45,
        "trending_down": 0.45,
        "volatile":      0.60,
    },
    "conservative": {
        "ranging":       0.50,
        "trending_up":   0.60,
        "trending_down": 0.60,
        "volatile":      0.80,
    },
    "aggressive": {
        "ranging":       0.25,
        "trending_up":   0.30,
        "trending_down": 0.30,
        "volatile":      0.40,
    },
}
VOLATILE_ATR_THRESHOLD = 0.005
TREND_SMA_THRESHOLD = 0.001
TRADE_LOG_CSV = "trade_logs.csv"
ENABLE_SUB_POSITIONING = True  # placeholder if you want sub-position logic
LONG_THRESHOLD = 0.6
SHORT_THRESHOLD = 0.4
TREND_MULTIPLIER      = 1.5
VOLATILY_MULTIPLIER = 2.0
RANGING_MULTIPLIER    = 0.5
DAILY_LOSS_LIMIT_PCT = 10.0
MAX_WORKERS = 4
DEFAULT_CHUNKS = 2
CHUNK_SPACING_PIPS = 10.0
OHLCV_BARS = 5000
INDICATOR_WEIGHTS_FILE = "indicator_weights.json"
TRADE_HISTORY_FILE = "trade_history.xlsx"
LOG_FILE = "log.txt"
BAR_COUNT = 600
SYMBOLS = [
    "EURUSD", "GBPUSD", "USDCHF", "USDJPY", "BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", "DOGUSD", "ADAUSD"]

DEFAULT_INDICATOR_WEIGHTS = {
    'RSI':       {'long': 1.0, 'short': 1.0},
    'MACD':      {'long': 1.0, 'short': 1.0},
    'MA':        {'long': 1.0, 'short': 1.0},
    'Stochastic':{'long': 1.0, 'short': 1.0},
    'Bollinger': {'long': 1.0, 'short': 1.0},
    'OBV':       {'long': 1.0, 'short': 1.0},
    'Ichimoku':  {'long': 1.0, 'short': 1.0}
}

MODEL_WEIGHTS = {
    'LSTM':      1.0,
    'CNN':       1.0,
    'SENTIMENT': 0.5
}

LSTM_MODEL_PATH = "models/{}_lstm_model.h5"
CNN_MODEL_PATH = "models/{}_cnn_model.h5"
SENTIMENT_MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
ACTIVE_SYMBOLS_PATH  = "active/active_symbols.json"
PHASE_BASED_FLIP_COOLDOWN_CANDLES = {
    "trending_up":   2,
    "trending_down": 2,
    "ranging":       5,
    "volatile":      8
}

# Dynamic trailing stops configuration
TRAILING_CONFIG = {
    "trending_up":   {"base_stop_factor": 2.0, "confidence_boost": 0.5},
    "trending_down": {"base_stop_factor": 2.0, "confidence_boost": 0.5},
    "ranging":       {"base_stop_factor": 1.5, "confidence_boost": 0.3},
    "volatile":      {"base_stop_factor": 3.0, "confidence_boost": 1.0}
}

# Partial TP configuration
PARTIAL_TP_CONFIG = {
    "trending_up":   {"tp_factor": 3.0, "confidence_boost": 1.0, "partial_close_ratio": 0.5},
    "trending_down": {"tp_factor": 3.0, "confidence_boost": 1.0, "partial_close_ratio": 0.5},
    "ranging":       {"tp_factor": 2.0, "confidence_boost": 0.5, "partial_close_ratio": 0.5},
    "volatile":      {"tp_factor": 4.0, "confidence_boost": 1.5, "partial_close_ratio": 0.5}
}

# Break-even configuration
BREAK_EVEN_CONFIG = {
    "trending_up":   {"be_factor": 1.5, "confidence_boost": 0.5},
    "trending_down": {"be_factor": 1.5, "confidence_boost": 0.5},
    "ranging":       {"be_factor": 1.0, "confidence_boost": 0.2},
    "volatile":      {"be_factor": 2.0, "confidence_boost": 1.0}
}

WIN_RATE_BOOST_THRESHOLD = 0.6
WIN_RATE_PENALTY_THRESHOLD = 0.4
BASIC_BOOST_MULTIPLIER   = 1.05
BASIC_PENALTY_MULTIPLIER = 0.95
MIN_SYNERGY_FACTOR       = 0.1
MAX_SYNERGY_FACTOR       = 2.0
PRUNE_MIN_TRADES         = 20
PRUNE_WIN_RATE           = 0.3
PERFORMANCE_TIME_DECAY = 720 # in minuti
PHASE_DECAY_MAP = {
    "volatile":      0.92,
    "trending_up":   0.97,
    "trending_down": 0.97,
    "ranging":       0.95
}
PHASE_DECAY_MIN = 0.85
PHASE_DECAY_MAX = 0.98
COMBO_DECAY_ATR_HIGH_THRESHOLD = 2.0
COMBO_DECAY_ATR_LOW_THRESHOLD = 0.5
COMBO_DECAY_STRONG_REDUCTION = 0.02
COMBO_DECAY_WEAK_BOOST = 0.01

PHASE_TUNER_DECAY_MAP = {
    "volatile":      0.95,
    "trending_up":   0.99,
    "trending_down": 0.99,
    "ranging":       0.98
}
PHASE_TUNER_DECAY_MIN = 0.95
PHASE_TUNER_DECAY_MAX = 0.99
DECAY_ATR_HIGH_THRESHOLD = 2.0   # Above this = faster decay
DECAY_ATR_LOW_THRESHOLD = 0.5    # Below this = slower decay
DECAY_MODIFIER_STRONG = 0.01     # How much to subtract if high ATR
DECAY_MODIFIER_WEAK = 0.005      # How much to add if low ATR

###############################
# MULTI-TIMEFRAME SETTINGS FOR AI SIGNALS
###############################
MULTI_TIMEFRAME_ENABLED = True
EXECUTION_TF_LABEL = "M5"  # Must match label in MULTI_TIMEFRAME_LIST
DEFAULT_TIMEFRAME = EXECUTION_TF_LABEL
MAX_TIMEFRAMES = 4
# Define the timeframes to use (up to MAX_TIMEFRAMES).
# Example: Using M5, M15, and H1
MULTI_TIMEFRAME_LIST = [
    (mt5.TIMEFRAME_M5, "M5"),
    (mt5.TIMEFRAME_M15, "M15"),
    (mt5.TIMEFRAME_H1, "H1"),
    (mt5.TIMEFRAME_H4, "H4")
]

# ============================
# 🔧 USER CONFIGURABLE SETTINGS
# ============================

# GENERAL CONTROL
DEBUG_MODE = True
TELEGRAM_NOTIFY_ON_RESTART = True
MAX_CONSECUTIVE_FAILURES = 3
EQUITY_ALERT_THRESHOLD = 100  # Adjust as needed

# SL/TP LOGIC
MIN_STOPLOSS_PCT = 3.0
MIN_TAKEPROFIT_PCT = 6.0 # Min TP as % of entry
SL_MULTIPLIER = 1.5  # ATR × multiplier = SL
TP_FACTOR = 2.0  # TP = SL × this + confidence boost
CONFIDENCE_BOOST_MULTIPLIER = 0.8

# DAILY PROFIT TARGET
DAILY_PROFIT_TARGET_PCT = 3.0
COOLDOWN_HOURS_AFTER_TARGET = 4

# CONSERVATIVE MODE SETTINGS
CONSERVATIVE_LOT_SIZE_REDUCTION = 0.5
CONSERVATIVE_SL_TP_TIGHTEN = 0.7
