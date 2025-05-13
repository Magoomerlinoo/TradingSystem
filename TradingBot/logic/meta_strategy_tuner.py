import settings 

class MetaStrategyTuner:
    def __init__(self):
        self.phase_performance = {
            "trending_up": {},
            "trending_down": {},
            "ranging": {},
            "volatile": {}
        }

    def track_indicator_performance(self, phase, indicators, profit, atr_value=1.0):
        decay_factor = self.get_dynamic_tuner_decay(phase, atr_value)
        for ind in indicators:
            perf = self.phase_performance[phase].setdefault(ind, {"wins":0, "losses":0, "net_profit":0.0})
            perf["wins"]        *= decay_factor
            perf["losses"]      *= decay_factor
            perf["net_profit"]  *= decay_factor
            perf["wins"]        += int(profit>0)
            perf["losses"]      += int(profit<=0)
            perf["net_profit"]  += profit

    def adjust_weights_by_phase(self, indicators, phase):
        local_weights = {}
        for ind in indicators:
            perf = self.phase_performance[phase].get(ind, {"wins":0,"losses":0,"net_profit":0.0})
            total = perf["wins"] + perf["losses"]
            local_weights[ind] = (perf["wins"]/total) if total>0 else 1.0
        total_weight = sum(local_weights.values()) if local_weights else 1.0
        for ind in indicators:
            factor = local_weights[ind]/total_weight if total_weight>0 else 1.0
            indicators[ind]['long']  *= factor
            indicators[ind]['short'] *= factor

    def get_dynamic_tuner_decay(self, phase, atr_value):
        base = settings.PHASE_TUNER_DECAY_MAP.get(phase, 0.98)

        # Step 1: applica l'esponenziale
        base = base ** atr_value

        # Step 2: aggiusta con un modificatore (opzionale)
        base += settings.DECAY_MODIFIER_WEAK

        # Step 3: limita entro i range
        return max(0.95, min(base, 0.99))