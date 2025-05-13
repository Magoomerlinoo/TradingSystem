import pandas as pd
import os
from models.lstm_model import LSTMModel
from models.cnn_model import CNNModel
from utils.training_data_builder import enrich_with_indicators

def retrain_from_csv(symbol, csv_path, is_raw=True, lookback=50):
    print(f"📂 Loading training data from: {csv_path}")

    if not os.path.exists(csv_path):
        print("❌ File does not exist.")
        return False

    try:
        df = pd.read_csv(csv_path)
        if is_raw:
            print("🧠 Enriching raw data with indicators...")
            df = enrich_with_indicators(df)
            df.dropna(inplace=True)

        # Save processed version
        save_path = f"data/processed/{symbol}_custom.csv"
        df.to_csv(save_path, index=False)
        print(f"✅ Saved processed CSV to: {save_path}")

        # Retrain models
        lstm = LSTMModel()
        cnn = CNNModel()

        lstm.retrain(symbol)
        cnn.retrain(symbol)

        print(f"✅ Retraining complete for {symbol}")
        return True

    except Exception as e:
        print(f"❌ Retraining failed: {e}")
        return False