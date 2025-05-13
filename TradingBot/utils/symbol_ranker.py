
import json
from datetime import datetime
import os

DEFAULT_STATS_FILE = "symbol_stats.json"

class SymbolRanker:
    def __init__(self, max_symbols=20, stats_file=DEFAULT_STATS_FILE, min_trades=5):
        self.max_symbols = max_symbols
        self.stats_file = stats_file
        self.min_trades = min_trades
        self.symbol_stats = self.load_stats()

    def load_stats(self):
        if os.path.exists(self.stats_file):
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {}

    def save_stats(self):
        with open(self.stats_file, 'w') as f:
            json.dump(self.symbol_stats, f, indent=2)

    def update_stats(self, symbol, profit):
        stats = self.symbol_stats.get(symbol, {"trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0})
        stats["trades"] += 1
        if profit > 0:
            stats["wins"] += 1
        else:
            stats["losses"] += 1
        stats["total_pnl"] += profit
        self.symbol_stats[symbol] = stats
        self.save_stats()

    def score_symbol(self, stats):
        if stats["trades"] < self.min_trades:
            return 0
        win_rate = stats["wins"] / stats["trades"]
        avg_pnl = stats["total_pnl"] / stats["trades"]
        return (win_rate * 100) + (avg_pnl * 2)

    def select_top_symbols(self, available_symbols=None):
        scored = []
        for symbol, stats in self.symbol_stats.items():
            if available_symbols is not None and symbol not in available_symbols:
                continue
            score = self.score_symbol(stats)
            scored.append((symbol, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored[:self.max_symbols]]
