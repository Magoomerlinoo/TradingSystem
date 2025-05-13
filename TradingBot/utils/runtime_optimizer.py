import MetaTrader5 as mt5
import pandas as pd
import os
import json

ACTIVE_SYMBOLS_PATH = os.path.join("active", "active_symbols.json")

def get_top_symbols(limit=20):
    # Assicuro la connessione a MT5
    if not mt5.initialize():
        print(f"[RuntimeOptimizer] MT5 init failed: {mt5.last_error()}")
        return []
    symbols = mt5.symbols_get()
    if symbols is None:
        print(f"[RuntimeOptimizer] symbols_get() returned None: {mt5.last_error()}")
        return []

    rankings = []
    for s in symbols:
        if not s.name or not s.visible:
            continue
        rates = mt5.copy_rates_from_pos(s.name, mt5.TIMEFRAME_M15, 0, 20)
        if rates is None or len(rates) < 2:
            continue
        df = pd.DataFrame(rates)
        if df.empty or df["close"].iloc[0] == 0:
            continue
        ret = (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0]
        rankings.append((s.name, ret))

    rankings.sort(key=lambda x: x[1], reverse=True)
    top = [sym for sym, _ in rankings[:limit]]

    os.makedirs(os.path.dirname(ACTIVE_SYMBOLS_PATH), exist_ok=True)
    with open(ACTIVE_SYMBOLS_PATH, "w") as f:
        json.dump(top, f, indent=2)
    print(f"[RuntimeOptimizer] Top {limit} symbols saved to {ACTIVE_SYMBOLS_PATH}")
    return top

def save_active_symbols(symbols):
    with open(ACTIVE_SYMBOLS_PATH, "w") as f:
        json.dump(symbols, f)

def load_active_symbols():
    if not os.path.exists(ACTIVE_SYMBOLS_PATH):
        return []
    with open(ACTIVE_SYMBOLS_PATH, "r") as f:
        return json.load(f)

def refresh_active_symbols():
    top = get_top_symbols()
    save_active_symbols(top)
    print(f"[RuntimeOptimizer] Refreshed top symbols: {top}")
