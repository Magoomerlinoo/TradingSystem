#!/usr/bin/env python3
"""
Sanity-check veloce dei modelli *.h5*.
Lancia:   python sanity_check.py   (nella root del progetto)
"""

import os, json, numpy as np, pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from settings import ACTIVE_SYMBOLS_PATH, LOOKBACK          # LOOKBACK=50
from utils.training_data_builder import load_training_data
from models.lstm_model import LSTMModel
from models.cnn_model  import CNNModel

TEST_SIZE  = 100          # barre da tenere fuori dal training
TIMEFRAMES = None         # usa settings.MULTI_TIMEFRAME_LIST

def eval_one(symbol: str):
    # ---------- prepara i dati ----------
    X, y = load_training_data(symbol,
                              lookback=LOOKBACK,
                              timeframes=TIMEFRAMES)
    if len(X) <= TEST_SIZE:
        print(f"[SKIP] {symbol}: solo {len(X)} campioni, troppi pochi per il test")
        return

    X_test, y_test = X[-TEST_SIZE:], y[-TEST_SIZE:]

    # ---------- carica i modelli ----------
    lstm = LSTMModel(f"models/{symbol}_lstm_model.h5")
    cnn  = CNNModel (f"models/{symbol}_cnn_model.h5")
    # ---------- predici ----------
    proba_cnn = cnn.model.predict(X_test, verbose=0)
    cnn_pred  = np.where(proba_cnn.max(axis=1) >= 0.70,
                        proba_cnn.argmax(axis=1),
                        0)
    
    proba_lstm = lstm.model.predict(X_test, verbose=0)
    lstm_pred  = np.where(proba_lstm.max(axis=1) >= 0.60,
                      proba_lstm.argmax(axis=1),
                      0)          # HOLD se bassa confidenza

    # ---------- metriche ----------
    for name, pred in [("LSTM", lstm_pred), ("CNN", cnn_pred)]:
        mask = y_test != 0
        y_oper = y_test[mask]; p_oper = pred[mask]
        acc = accuracy_score(y_oper, p_oper) if len(y_oper) else float("nan")
        cm  = confusion_matrix(y_oper, p_oper, labels=[1, 2])

        print(f"\n[{symbol}] {name}")
        print(f"  campioni test totali    : {len(y_test)}")
        print(f"  segnali operativi (≠0)  : {len(y_oper)}")
        print(f"  accuracy up/down        : {acc:.3f}")
        print("  confusion matrix (righe=verità, colonne=pred) [UP,DOWN]")
        print(cm)

        # -------- precision / recall / f1 ----------------
        print(classification_report(
            y_test,               # vere etichette
            pred,                 # previsioni correnti
            labels=[1, 2],        # valutiamo solo i trade
            digits=3,
            zero_division=0       # evita warning se colonna vuota
        ))

if __name__ == "__main__":
    with open(ACTIVE_SYMBOLS_PATH) as f:
        symbols = json.load(f)

    for sym in symbols:
        try:
            eval_one(sym)
        except Exception as e:
            print(f"[ERROR] {sym}: {e}")