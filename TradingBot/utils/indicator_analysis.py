import pandas as pd
from collections import defaultdict
from itertools import combinations

def learn_indicator_combos(symbol, log_path="trade_logs.csv", min_trades=3):
    df = pd.read_csv(log_path)

    # Filter for the right symbol
    df = df[df["symbol"] == symbol]

    # Make sure 'used_indicators' is valid
    df = df[df["used_indicators"].notnull()]
    df["used_indicators"] = df["used_indicators"].apply(eval)

    combo_stats = defaultdict(lambda: {"count": 0, "profit": 0.0})

    for _, row in df.iterrows():
        indicators = row["used_indicators"]
        profit = row["profit"]

        # Learn from all combos (size 1 to N)
        for r in range(1, len(indicators) + 1):
            for combo in combinations(sorted(indicators), r):
                combo_stats[combo]["count"] += 1
                combo_stats[combo]["profit"] += profit

    # Compute average profit per combo
    combo_perf = {
        combo: round(stats["profit"] / stats["count"], 4)
        for combo, stats in combo_stats.items()
        if stats["count"] >= min_trades
    }

    # Sort combos by profitability
    sorted_perf = dict(sorted(combo_perf.items(), key=lambda item: -abs(item[1])))

    return sorted_perf
