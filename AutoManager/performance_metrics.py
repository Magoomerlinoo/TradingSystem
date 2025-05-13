# performance_metrics.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import datetime
from collections import deque
from AutoManager import settings_manager
# Stato accumulato
bot_stats_window = deque()

def calculate_max_drawdown(equity_curve):
    max_drawdown = 0
    peak = equity_curve[0]
    for value in equity_curve:
        peak = max(peak, value)
        drawdown = (peak - value) / peak
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown

def update_bot_stats(trades: list[dict], current_equity: float) -> dict:
    """
    trades = [{timestamp, profit, correct}, ...]
    current_equity = equity attuale
    """
    now = datetime.datetime.utcnow()

    profits = [t["profit"] for t in trades]
    correct = [t["correct"] for t in trades]

    total = len(correct)
    wins = sum(correct)
    winrate = wins / total if total else 1.0
    avg_ev = sum(profits) / total if total else 0.0

    max_dd = calculate_max_drawdown([s["equity"] for s in bot_stats_window] + [current_equity])
    daily_profit = avg_ev * total  # in assenza di decadimento temporale, ev * numero trade

    bot_stats_window.append({
        "timestamp": now,
        "equity": current_equity
    })

    return {
        "winrate": winrate,
        "avg_trade_ev": avg_ev,
        "max_drawdown": max_dd,
        "daily_profit": daily_profit
    }

def update_model_accuracy(model_results: dict) -> dict:
    return {
        "lstm": model_results.get("lstm_accuracy", 1.0)
    }


def update_market_state(current_vol: float, past_vol_list: list[float]) -> dict:
    return {
        "current_volatility": current_vol,
        "avg_volatility": sum(past_vol_list) / len(past_vol_list) if past_vol_list else 0.0
    }

import glob
import json

def load_recent_trades(max_files: int = 10) -> list[dict]:
    """
    Carica gli ultimi N file di trade (es. logs JSON), li unisce in una lista.
    Ogni trade è un dizionario con chiavi: profit, correct (bool), timestamp, ecc.
    """
    logs_path = os.path.join("trade_logs")  # personalizza se il path è diverso
    pattern = os.path.join(logs_path, "*.json")
    files = sorted(glob.glob(pattern), reverse=True)[:max_files]

    trades = []
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    trades.extend(data)
                elif isinstance(data, dict):
                    trades.append(data)
        except Exception as e:
            print(f"[load_recent_trades] Errore su {fp}: {e}")
            continue

    return trades

# Trigger checks

def is_winrate_too_low(winrate: float) -> bool:
    return winrate < settings_manager.WINRATE

def is_drawdown_excessive(drawdown: float) -> bool:
    return drawdown > settings_manager.MAX_ALLOWED_DRAWDOWN

def is_daily_profit_low(daily_profit: float) -> bool:
    return daily_profit < settings_manager.DAILY_PROFIT_TARGET

def is_avg_ev_too_low(avg_ev: float) -> bool:
    return avg_ev < settings_manager.RITORNO_PER_TRADE

def is_lstm_accuracy_low(lstm_acc: float) -> bool:
    return lstm_acc < settings_manager.LSTM_ACCURACY