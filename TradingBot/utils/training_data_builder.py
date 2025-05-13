# utils/training_data_builder.py
import os
import json
from datetime import datetime
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import settings
from logic.fusion_engine import get_market_phase
from utils.generate_training_csv import enrich_with_indicators

# Quanti bars scaricare
BARS = settings.OHLCV_BARS

# Mappa label → codice MT5
TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}

def fetch_ohlcv_mt5(symbol: str, tf_label: str, bars: int) -> pd.DataFrame:
    code = TF_MAP[tf_label]
    if not mt5.initialize():
        raise RuntimeError("MT5 init failed")
    rates = mt5.copy_rates_from(symbol, code, datetime.now(), bars)
    mt5.shutdown()
    df = pd.DataFrame(rates)
    if df.empty:
        return df
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def fetch_or_aggregate(symbol: str, tf_label: str, bars: int) -> pd.DataFrame:
    df = fetch_ohlcv_mt5(symbol, tf_label, bars)
    if not df.empty:
        return df

    if tf_label == "M15":
        df5 = fetch_ohlcv_mt5(symbol, "M5", bars * 3)
        if df5.empty:
            return pd.DataFrame()
        df5.set_index('time', inplace=True)
        df15 = df5.resample("15T").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "tick_volume": "sum"
        }).dropna().reset_index()
        # ——— FILL MISSING RAW COLUMNS ———
        df15['spread'] = 0
        df15['real_volume'] = df15['tick_volume']
        # alias tick_volume → volume
        df15['volume'] = df15['tick_volume']
        return df15

    return pd.DataFrame()

def build_from_symbol(symbol: str):
    """Costruisci i CSV per un singolo simbolo."""
    # lista dei timeframe
    if settings.MULTI_TIMEFRAME_ENABLED:
        tf_list = [label for _, label in settings.MULTI_TIMEFRAME_LIST][: settings.MAX_TIMEFRAMES]
    else:
        tf_list = [settings.DEFAULT_TIMEFRAME]

    os.makedirs("data/processed", exist_ok=True)

    for tf_label in tf_list:
        out_csv = f"data/processed/{symbol}_{tf_label}.csv"
        if os.path.exists(out_csv):
            print(f"[DATA] Skipping {out_csv} (already exists)")
            continue

        print(f"[DATA] Building {symbol} @ {tf_label}…")
        try:
            df = fetch_or_aggregate(symbol, tf_label, BARS)
            if df.empty:
                raise ValueError("no data")

            df = enrich_with_indicators(df)
            df.to_csv(out_csv, index=False)
            print(f"[DATA] Saved {len(df)} rows to {out_csv}")

        except Exception as e:
            print(f"[DATA] FAILED for {symbol} {tf_label}: {e}")

def build_all_symbols():
    """Costruisci i CSV per tutti i simboli attivi secondo le impostazioni in settings.py."""
    # 1) carica simboli attivi
    with open(settings.ACTIVE_SYMBOLS_PATH, "r") as f:
        symbols = json.load(f)

    # 2) definisci la lista di timeframe
    if settings.MULTI_TIMEFRAME_ENABLED:
        # prendi al massimo MAX_TIMEFRAMES elementi
        tf_list = settings.MULTI_TIMEFRAME_LIST[: settings.MAX_TIMEFRAMES]
    else:
        # se multi‐TF spento, prendi solo quello di default
        tf_list = [
            (None, settings.DEFAULT_TIMEFRAME)
        ]

    # 3) assicurati che la cartella esista
    os.makedirs("data/processed", exist_ok=True)

    # 4) per ogni simbolo e timeframe
    for symbol in symbols:
        for _, tf_label in tf_list:
            out_csv = f"data/processed/{symbol}_{tf_label}.csv"

            # 4.a) se già esiste, salta
            if os.path.exists(out_csv):
                print(f"[DATA] Skipping {out_csv} (already exists)")
                continue

            print(f"[DATA] Building {symbol} @ {tf_label}…")
            try:
                # 4.b) fetch (o aggregate) + enrich + save
                df = fetch_or_aggregate(symbol, tf_label, settings.OHLCV_BARS)
                if df.empty:
                    raise ValueError("no data returned")

                df = enrich_with_indicators(df)
                df.to_csv(out_csv, index=False)
                print(f"[DATA] Saved {len(df)} rows to {out_csv}")

            except Exception as e:
                print(f"[DATA] FAILED for {symbol} {tf_label}: {e}")

def load_training_data(symbol: str,
                       lookback: int = 50,
                       timeframes: list[str] | None = None,
                       min_samples: int = 50):
    """
    Loads X, y for symbol by stacking all enabled timeframes,
    discovering every indicator column present in the CSVs.
    """
    if timeframes is None:
        # pull the labels from settings.MULTI_TIMEFRAME_LIST
        timeframes = [label for _, label in settings.MULTI_TIMEFRAME_LIST]

    # Build a list of the base indicator names we care about
    # e.g. ['RSI', 'MACD', 'MA', ...]
    # Colonne di base (chiusura + tutti gli indicatori definiti in settings)
    base_inds = list(settings.DEFAULT_INDICATOR_WEIGHTS.keys())
    core_prices  = ['close', 'high', 'low']  
    dfs = []
    for tf in timeframes:
        path = f"data/processed/{symbol}_{tf}.csv"
        if not os.path.exists(path):
            print(f"[TRAIN_DATA] Missing: {path}")
            return np.array([]), np.array([])

        df = pd.read_csv(path)

        # sempre tieni close / high / low
        feature_cols = core_prices.copy()

        # poi aggiungi dinamicamente gli indicatori
        for col in df.columns:
            for ind in base_inds:
                if ind.upper() in col.upper() and col not in feature_cols:
                    feature_cols.append(col)
        # If for some reason we found none besides 'close', abort:
        if len(feature_cols) <= 1:
            print(f"[TRAIN_DATA] No indicator columns found in {path}")
            return np.array([]), np.array([])

        # Drop rows with NaNs in any of the feature columns
        df = df.dropna(subset=feature_cols)

        # Rename so each column becomes e.g. "RSI_14_M15" for timeframe stacking
        renamed = {col: f"{col}_{tf}" for col in feature_cols}
        df = df[feature_cols].rename(columns=renamed)

        dfs.append(df.reset_index(drop=True))

    # Combine horizontally on index
    df_combined = pd.concat(dfs, axis=1).dropna()

    # ------------------------------------------------------------------
    phase   = get_market_phase(symbol)              # 'ranging', 'trending_up', …
    mode    = settings.STRATEGY_MODE                # di solito "normal"
    mult    = settings.ATR_MULTIPLIER[phase]        # coefficiente da settings

    # calcola ATR (High-Low sui dati M5, periodo definito in settings)
    hl = df_combined[[f"high_{timeframes[0]}", f"low_{timeframes[0]}"]]
    close = df_combined[f"close_{timeframes[0]}"]

    # True Range (3 vettori) in DataFrame, poi max riga-per-riga
    tr_df = pd.DataFrame({
        "hl":  hl.iloc[:,0] - hl.iloc[:,1],
        "hc": (hl.iloc[:,0] - close.shift()).abs(),
        "cl": (close.shift() - hl.iloc[:,1]).abs()
    })
    true_range = tr_df.max(axis=1)                   # Series pandas

    atr = true_range.rolling(settings.ATR_PERIOD).mean()
    # ------------------------------------------------------------------

    X, y = [], []
    for i in range(lookback, len(df_combined) - 1):
        X.append(df_combined.iloc[i - lookback:i].values)

        # ------------------------------------------------------------------
        if pd.isna(atr.iloc[i]):          # ATR non ancora disponibile
            continue                      # passa all'indice successivo
        # ------------------------------------------------------------------

        close_now  = df_combined.iloc[i - 1][f"close_{timeframes[0]}"]
        close_next = df_combined.iloc[i][f"close_{timeframes[0]}"]

        pct_change = (close_next - close_now) / close_now  # <- percentuale

        thr_pct = (atr.iloc[i] / close_now) * mult

        if pct_change > thr_pct:
            y.append(1)
        elif pct_change < -thr_pct:
            y.append(2)
        else:
            y.append(0)

    # ---------------------------------------------------------------
    X = np.array(X)          # ① converti subito
    y = np.array(y)
    # ---------------------------------------------------------------

    from sklearn.utils import resample
    counts  = np.bincount(y, minlength=3)         # [c0, c1, c2]
    target = int(counts[0] * 0.7)

    def up(class_id):
        deficit = target - counts[class_id]
        if deficit <= 0:
            return np.empty((0, *X.shape[1:])), np.empty(0, dtype=y.dtype)
        X_up = resample(X[y == class_id],
                        replace=True,
                        n_samples=deficit,
                        random_state=42)
        y_up = np.full(deficit, class_id, dtype=y.dtype)
        return X_up, y_up

    X1_up, y1_up = up(1)
    X2_up, y2_up = up(2)

    # ---------------------------------------------------------------
    # ② aggiungi i campioni duplicati
    X = np.concatenate([X, X1_up, X2_up])
    y = np.concatenate([y, y1_up, y2_up])
    # ---------------------------------------------------------------

    if len(X) < min_samples:
        print(f"[TRAIN_DATA] Not enough training samples for {symbol}")
        return np.array([]), np.array([])
    # ------------------- DEBUG: stampo mult e distribuzione classi ----------------
    if settings.DEBUG_BUILD:
    # mult è ancora disponibile perché lo calcoli fuori dal loop
        print(f"{symbol:7}  mult usato = {mult:.3f}")
        counts = np.bincount(y, minlength=3)
        print(f"           classi 0:{counts[0]}  1:{counts[1]}  2:{counts[2]}  (tot {len(y)})")
        # -------------------------------------------------------------------------------

    return X, y


if __name__ == "__main__":
    import json, settings
    from collections import Counter

    with open(settings.ACTIVE_SYMBOLS_PATH) as f:
        symbols = json.load(f)

    for sym in symbols:
        _, y = load_training_data(sym)
        c = Counter(y)
        total = sum(c.values())
        print(f"{sym:7}  0:{c[0]}  1:{c[1]}  2:{c[2]}  (tot {total})")