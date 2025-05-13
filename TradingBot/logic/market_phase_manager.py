# logic/market_phase_manager.py
import settings

class MarketPhaseManager:
    def __init__(self):
        self.symbol_phases = {}
        self.phase_performance = {
            "trending_up":    {"wins":0, "losses":0},
            "trending_down":  {"wins":0, "losses":0},
            "ranging":        {"wins":0, "losses":0},
            "volatile":       {"wins":0, "losses":0}
        }
        self.trend_multiplier = settings.TREND_MULTIPLIER
        self.volatility_multiplier = settings.VOLATILY_MULTIPLIER
        self.ranging_multiplier = settings.RANGING_MULTIPLIER

    def detect_phase_for_symbol(self, symbol, close_series, short_ma, long_ma, atr):
        if len(close_series) < 2:
            return self.symbol_phases.get(symbol, "ranging")

        price_now  = close_series.iloc[-1]
        price_prev = close_series.iloc[-2]
        price_change = abs(price_now - price_prev)

        if price_now > long_ma and price_change > atr * self.trend_multiplier:
            phase = "trending_up"
        elif price_now < short_ma and price_change > atr * self.trend_multiplier:
            phase = "trending_down"
        elif price_change < atr * self.ranging_multiplier:
            phase = "ranging"
        elif price_change > atr * self.volatility_multiplier:
            phase = "volatile"
        else:
            phase = "ranging"

        self.symbol_phases[symbol] = phase
        return phase

    def update_symbol_phase_performance(self, symbol, phase, pl_pct):
        if phase not in self.phase_performance:
            self.phase_performance[phase] = {"wins":0, "losses":0}
        if pl_pct > 0:
            self.phase_performance[phase]["wins"] += 1
        else:
            self.phase_performance[phase]["losses"] += 1

    def adjust_phase_thresholds(self, feedback):
        inv_feedback = 1.0 / feedback
        self.trend_multiplier      *= inv_feedback
        self.volatility_multiplier *= inv_feedback
        self.ranging_multiplier    *= inv_feedback