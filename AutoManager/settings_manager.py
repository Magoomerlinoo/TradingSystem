# settings_manager.py

"""
Configurazioni globali per AutoManager
"""

# ==============================
# === GPT-4 API SETTINGS ===
# ==============================

# Chiave API per OpenAI
OPENAI_API_KEY = "placeholder"

# Routing motore OpenAI
# Se True, per le patch di codice useremo Codex anziché GPT-4
REQUEST_CODE_PATCH = False

# Abilita chiamate GPT-4 per suggerimenti automatici
CALL_GPT_FOR_SUGGESTIONS = False

AUTO_APPLY_PATCHES = False

# ==============================
# === GIT AUTO-PUSH SETTINGS ===
# ==============================

# Abilita git add/commit/push automatico dopo ogni patch
ENABLE_AUTO_GIT_PUSH = False

# Branch Git di default
GIT_BRANCH = "master"

# ==============================
# === TELEGRAM BOT SETTINGS ===
# ==============================

# Token e chat ID per notifiche Telegram
TELEGRAM_BOT_TOKEN = "placeholder"
TELEGRAM_CHAT_ID    = "placeholder"

# ==============================
# === PERFORMANCE TARGETS ===
# ==============================
LSTM_ACCURACY       = 1
 # winrate minimo accettabile (es. 60%)
WINRATE             = 0.60
# EV minimo per trade (1.5%)
RITORNO_PER_TRADE   = 0.015  
# Precisione minima desiderata (es. 0.70 = 70%)
PRECISION_TARGET      = 0.70
# Profitto medio giornaliero desiderato (es. 0.03 = 3%)
DAILY_PROFIT_TARGET   = 0.03
# Drawdown massimo tollerato (es. 0.20 = 20%)
MAX_ALLOWED_DRAWDOWN  = 0.20
# ==============================
# === SUPERVISOR SETTINGS ===
# ==============================

# Intervallo di monitoraggio (secondi)
MONITOR_INTERVAL_SECONDS = 600
# ==============================
# === MANAGER LOCK SYSTEM ===
# ==============================

# Previene patch ripetute troppo ravvicinate
LOCK_SYSTEM = {
    # Modalità di lock: 'cycles' o 'hours'
    'mode': 'cycles',
    # Numero di cicli ore in base a mode
    'value': 6
}

# ==============================
# === POST-MODIFICATION VALIDATION ===
# ==============================

# Configurazione per validazione delle patch prima di conferma
POST_VALIDATION = {
    'enabled': True,
    'general_settings': {
        # N. di cicli di monitoraggio prima di confermare la patch
        'validation_window_cycles': 3,
        # Miglioramento minimo richiesto (pct) per passare la convalida
        'minimum_improvement_required': 0.02,
    },
    'weights': {
        'minor_param_change':   {'cycles': 3,  'improvement': 0.01},
        'major_logic_change':   {'cycles': 6,  'improvement': 0.03},
        'strategy_switch':      {'cycles': 10, 'improvement': 0.05},
    }
}

# ==============================
# === DYNAMIC LEVERAGE SETTINGS ===
# ==============================

# Abilita gestione dinamica della leva
ENABLE_DYNAMIC_LEVERAGE = True
# Leva massima applicabile al capitale
MAX_DYNAMIC_LEVERAGE    = 5.0

# ==============================
# === PROGRESSIVE SCALING SETTINGS ===
# ==============================

# Abilita scaling progressivo delle posizioni
ENABLE_PROGRESSIVE_SCALING = True
# Percentuale di profitto per attivare scrolling
SCALING_TRIGGER_PERCENT    = 0.50  # 50%
# Frazione del lotto iniziale da aggiungere per step
SCALING_FACTOR             = 0.20  # 20%
# Massimo numero di step di scaling consecutivi
MAX_SCALING_STEPS          = 5

# ==============================
# === ALTRE IMPOSTAZIONI UTENTE ===
# ==============================

CONTEXT_INCLUDE_CODE = True
AUTO_CONTEXT_PROMPT = True
# Definisci qui eventuali altre costanti o flag configurabili a livello di Manager

# Fine settings_manager.py
