import pandas as pd
import pandas_ta as ta
import os
from datetime import datetime
import settings
import MetaTrader5 as mt5
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_ohlcv(symbol, timeframe=settings.EXECUTION_TF_LABEL, bars=settings.OHLCV_BARS):
    # timeframe può essere label ("M5") o code (mt5.TIMEFRAME_M5)
    tf_map = { label: code for code,label in settings.MULTI_TIMEFRAME_LIST }
    code = tf_map.get(timeframe, timeframe)  # se è code, lo lascia
    if not mt5.initialize(): raise RuntimeError("Failed to initialize MT5")
    rates = mt5.copy_rates_from_pos(symbol, code, 0, bars)
    mt5.shutdown()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def enrich_with_indicators(df):

        # ASSICURIAMO CHE LE COLONNE ESISTANO
    if 'volume' not in df:
        df['volume'] = df.get('tick_volume', 0)
    if 'spread' not in df:
        df['spread'] = 0
    if 'real_volume' not in df:
        df['real_volume'] = df.get('tick_volume', 0)
    # adesso procedi con i calcoli TA senza più NoneType
    """
    Appends a broad set of indicators to df in-place.
    You can add or remove any ta.* calls here to match your original list.
    """
    # ** Price **
    # (no change)

    # ** Trend Indicators **
    df.ta.sma(length=20, append=True)           # sma_20
    df.ta.ema(length=50, append=True)           # ema_50
    df.ta.macd(fast=12, slow=26, signal=9, append=True)   # macd_12_26_9, macds_12_26_9, macdh_12_26_9

    # ** Momentum Indicators **
    df.ta.rsi(length=14, append=True)           # rsi_14
    df.ta.stoch(length=14, append=True)         # STOCH_k_14_3_3, STOCH_d_14_3_3
    df.ta.stochrsi(length=14, append=True)      # STOK_14, STOD_14

    # ** Volatility Indicators **
    df.ta.atr(length=14, append=True)           # atr_14
    df.ta.bbands(length=20, std=2, append=True) # bbands_20_2 (bbm, bbl, bbh)

    # ** Volume Indicators **
    df.ta.obv(append=True)

    return df

def save_processed_csv(symbol, tf_label, df):
    folder = "data/processed"
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{symbol}_{tf_label}.csv")
    df.to_csv(path, index=False)
    print(f"[DATA] Saved: {path}")

def generate_for_symbol(symbol):
    for tf_code, label in MULTI_TIMEFRAME_LIST:
        print(f"[DATA] Generating {symbol} - {label}...")
        df = fetch_ohlcv(symbol, timeframe=tf_code)
        if df is not None:
            df = enrich_with_indicators(df)
            df.dropna(inplace=True)
            save_processed_csv(symbol, label, df)

def generate_all_symbols():
    if not mt5.initialize():
        print("MT5 init failed.")
        return

    print(f"⏱️ Generating data for {len(settings.SYMBOLS)} symbols in parallel...")

    with ThreadPoolExecutor(settings.MAX_WORKERS) as executor:  # Adjust workers based on CPU
        futures = [executor.submit(generate_for_symbol, symbol) for symbol in settings.SYMBOLS]
        for future in as_completed(futures):
            try:
                future.result()  # will raise exception if generate_for_symbol failed
            except Exception as e:
                print(f"[ERROR] Symbol generation failed: {e}")

    mt5.shutdown()