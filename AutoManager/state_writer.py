# state_writer.py

import os
import json
import random
from datetime import datetime

STATE_PATH = "C:\Users\Administrator\Desktop\TradingBot/state.json"

def mock_bot_performance():
    """Simula l'output del bot con metriche reali."""
    return {
        "daily_profit": round(random.uniform(0.01, 0.05), 3),
        "signal_precision": round(random.uniform(0.6, 0.9), 2),
        "drawdown": round(random.uniform(0.05, 0.2), 2),
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def write_state(metrics):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

def update_state():
    metrics = mock_bot_performance()
    write_state(metrics)
    print(f"[StateWriter] Stato aggiornato: {metrics}")

if __name__ == "__main__":
    update_state()
