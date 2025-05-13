#!/usr/bin/env python3
import os
import json
from settings import ACTIVE_SYMBOLS_PATH
from models.lstm_model import LSTMModel
from models.cnn_model import CNNModel
from utils.training_data_builder import build_from_symbol

def main():
    # 1) Carica dinamicamente la lista dei simboli attivi
    if not os.path.exists(ACTIVE_SYMBOLS_PATH):
        print(f"Active symbols file not found at {ACTIVE_SYMBOLS_PATH}")
        return

    with open(ACTIVE_SYMBOLS_PATH, "r") as f:
        symbols = json.load(f)

    # 2) Costruisci (se mancano) i CSV con i dati + indicatori
    for sym in symbols:
        print(f"[DATA] Building training data for {sym}…")
        try:
            build_from_symbol(sym)
        except Exception as e:
            print(f"[DATA] FAILED for {sym}: {e}")

    # 3) Instanzia i modelli (usano al loro interno build/retrain)
    lstm_model = LSTMModel()
    cnn_model = CNNModel()

    # 4) Loop di retraining (loro gestiscono internamente se ci sono dati a sufficienza)
    for sym in symbols:
        print(f"[TRAIN] Retraining LSTM for {sym}…")
        try:
            lstm_model.retrain(sym)
            print(f"[TRAIN] ✅ LSTM retrained and saved for {sym}")
        except Exception as e:
            print(f"[TRAIN] Error during LSTM retraining for {sym}: {e}")

        print(f"[TRAIN] Retraining CNN for {sym}…")
        try:
            cnn_model.retrain(sym)
            print(f"[TRAIN] ✅ CNN retrained and saved for {sym}")
        except Exception as e:
            print(f"[TRAIN] Error during CNN retraining for {sym}: {e}")

if __name__ == "__main__":
    main()