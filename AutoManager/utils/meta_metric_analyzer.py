import sqlite3
from typing import Dict, List
import statistics
from datetime import datetime
from collections import defaultdict

DB_PATH = "data/bot_data.db"

def load_recent_snapshots(metric: str, limit: int = 20) -> List[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, value
            FROM performance_snapshot
            WHERE metric = ?
            ORDER BY id DESC
            LIMIT ?
        """, (metric.upper(), limit))
        rows = cur.fetchall()
    return [{"timestamp": ts, "value": val} for ts, val in reversed(rows)]

def analyze_metric_trend(metric: str, threshold: float = 0.05) -> str:
    data = load_recent_snapshots(metric)
    if len(data) < 4:
        return f"⚠️ Dati insufficienti per valutare {metric}"

    values = [entry["value"] for entry in data]
    delta = values[-1] - values[0]
    avg = statistics.mean(values)

    if abs(delta) < threshold:
        return f"↔️ {metric}: stabile (media: {avg:.4f})"
    elif delta > 0:
        return f"📈 {metric}: in miglioramento (+{delta:.4f})"
    else:
        return f"📉 {metric}: in calo ({delta:.4f})"

def generate_context_for_gpt() -> str:
    metrics = [
        "WINRATE", "DAILY_PROFIT", "AVG_TRADE_EV",
        "MAX_DRAWDOWN", "LSTM_ACCURACY", "PRECISION"
    ]
    context = ["📊 **Analisi metrica automatica (ultimi snapshot)**"]
    for metric in metrics:
        context.append(analyze_metric_trend(metric))
    return "\n".join(context)

if __name__ == "__main__":
    print(generate_context_for_gpt())
