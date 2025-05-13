# logic/fusion_engine.py

import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
import settings

def get_market_phase(symbol: str,
                     timeframe_label: str = None,
                     bars: int = settings.BAR_COUNT) -> str:
    """
    Determina la fase di mercato per `symbol`:
      - 'volatile'      se ATR/close medio supera VOLATILE_ATR_THRESHOLD
      - 'trending_up'   se SMA50 > SMA200 di almeno TREND_SMA_THRESHOLD
      - 'trending_down' se SMA50 < SMA200 di almeno TREND_SMA_THRESHOLD
      - 'ranging'       altrimenti
    """
    # 1) Scegli il label del timeframe
    tf_label = (timeframe_label or settings.EXECUTION_TF_LABEL).upper()

    # 2) Mappa label→codice MT5
    tf_map = { label: code for code, label in settings.MULTI_TIMEFRAME_LIST }
    if tf_label not in tf_map:
        raise ValueError(f"Label TF non valida: {tf_label}")
    tf_code = tf_map[tf_label]

    # 3) Scarica le ultime `bars` barre da MT5
    if not mt5.initialize():
        raise RuntimeError("MT5 init failed")
    rates = mt5.copy_rates_from(symbol, tf_code, datetime.now(), bars)
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"Nessun dato MT5 per {symbol} @ {tf_label}")

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    close = df['close']
    high  = df['high']
    low   = df['low']

    # 4) Calcola l'ATR a 14 barre
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low  - prev_close).abs()
    tr  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]

    # 5) Rapporto ATR / prezzo medio
    rel_atr = atr / close.mean()

    # 6) Calcola SMA50 e SMA200
    sma50  = close.rolling(50).mean().iloc[-1]
    sma200 = close.rolling(200).mean().iloc[-1]
    rel_sma_diff = (sma50 - sma200) / sma200

    # 7) Soglie lette da settings.py
    v_thr = settings.VOLATILE_ATR_THRESHOLD
    s_thr = settings.TREND_SMA_THRESHOLD

    # 8) Decisione finale
    if rel_atr > v_thr:
        return "volatile"
    if rel_sma_diff >  s_thr:
        return "trending_up"
    if rel_sma_diff < -s_thr:
        return "trending_down"
    return "ranging"

def fuse_probabilities(classical_signals, lstm_pred=None, cnn_pred=None, sentiment=None, symbol_weights=None):
    """
    Fuse classical + AI signals into final probability, direction, confidence, and used indicators.
    Returns (direction, confidence, final_probability, used_indicators).
    """
    used_indicators = []
    long_score = 0.0
    short_score = 0.0

    if symbol_weights is None:
        symbol_weights = settings.DEFAULT_INDICATOR_WEIGHTS

    # Classical indicators scoring (continuous signals assumed [0-1])
    for ind, prob in classical_signals.items():
        # Use symbol weights
        long_weight = symbol_weights.get(ind, {'long':1.0})['long']
        short_weight = symbol_weights.get(ind, {'short':1.0})['short']
        
        long_score += prob * long_weight
        short_score += (1 - prob) * short_weight
        
        if prob > 0.6 or prob < 0.4:
            used_indicators.append(ind)

    # AI Models scoring (probabilities [0-1])
    model_weights = settings.MODEL_WEIGHTS
    
    # LSTM Model
    if lstm_pred is not None:
        long_score += lstm_pred * model_weights['LSTM']
        short_score += (1 - lstm_pred) * model_weights['LSTM']
        used_indicators.append('LSTM')

   # CNN Model
    if cnn_pred is not None:
        # Handle string pattern predictions
        if isinstance(cnn_pred, str):
            pattern_weights = {
                "double_bottom": 0.8,
                "head_and_shoulders": 0.3,
                "no_pattern": 0.0
            }
            cnn_pred = pattern_weights.get(cnn_pred.lower(), 0.0)

        try:
            long_score += cnn_pred * model_weights['CNN']
            short_score += (1 - cnn_pred) * model_weights['CNN']
            used_indicators.append('CNN')
        except TypeError as e:
            print(f"[Fusion Engine] CNN prediction type error: {e} (cnn_pred: {cnn_pred})")

    # Sentiment
    if sentiment is not None:
        sentiment_scaled = (sentiment + 1) / 2 if sentiment < 0 else sentiment
        long_score += sentiment_scaled * model_weights['SENTIMENT']
        short_score += (1 - sentiment_scaled) * model_weights['SENTIMENT']
        used_indicators.append('SENTIMENT')

    # Final Direction
    if long_score > short_score:
        direction = 'long'
    elif short_score > long_score:
        direction = 'short'
    else:
        direction = 'hold'

    total_score = long_score + short_score
    final_probability = long_score / total_score if total_score != 0 else 0.5
    confidence = abs(long_score - short_score) / total_score if total_score != 0 else 0

    return direction, confidence, final_probability, used_indicators