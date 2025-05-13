# logic/meta_indicator_learning.py
class MetaIndicatorLearning:
    def __init__(self):
        self.combination_performance = {}
        self.group_bonus = {}
        self.min_weight = 0.1
        self.max_weight = 2.0

    def track_combination(self, indicators, phase, direction, profit, atr_value=1.0):
        combo_key = tuple(sorted(indicators))
        self.combination_performance.setdefault(combo_key, {}).setdefault(phase, {'wins':0, 'losses':0})

        decay_factor = self.get_dynamic_combo_decay(phase, atr_value)
        for ph in self.combination_performance[combo_key]:
            self.combination_performance[combo_key][ph]['wins']   *= decay_factor
            self.combination_performance[combo_key][ph]['losses'] *= decay_factor

        if profit > 0:
            self.combination_performance[combo_key][phase]['wins'] += 1
        else:
            self.combination_performance[combo_key][phase]['losses'] += 1

    def evaluate_combination(self, indicators, phase):
        combo_key = tuple(sorted(indicators))
        stats = self.combination_performance.get(combo_key, {}).get(phase, {})
        total = stats.get('wins', 0) + stats.get('losses', 0)
        if total < 1:
            return 0.0
        return stats['wins'] / total

    def reward_synergistic_combinations(self, indicator_weights, indicators, phase, direction, profit=0.0):
        combo_key = tuple(sorted(indicators))
        self.group_bonus.setdefault(combo_key, {'long': 1.0, 'short': 1.0})
        win_rate = self.evaluate_combination(indicators, phase)

        self.group_bonus[combo_key][direction] *= 0.99
        if win_rate > 0.6:
            self.group_bonus[combo_key][direction] *= 1.05
        elif win_rate < 0.4:
            self.group_bonus[combo_key][direction] *= 0.95

        synergy_factor = self.group_bonus[combo_key][direction]
        synergy_factor *= (1 + (profit/100.0)) if profit > 0 else max(0.5, (1 + profit/100.0))
        synergy_factor = max(self.min_weight, min(synergy_factor, self.max_weight))
        self.group_bonus[combo_key][direction] = synergy_factor

        for indicator in indicators:
            if indicator not in indicator_weights:
                indicator_weights[indicator] = {'long': 1.0, 'short': 1.0}
            indicator_weights[indicator][direction] *= synergy_factor
            indicator_weights[indicator][direction] = max(
                self.min_weight, min(indicator_weights[indicator][direction], self.max_weight)
            )

    def prune_ineffective_combinations(self):
        to_prune = []
        for combo, data in self.combination_performance.items():
            total_trades = sum(stat['wins'] + stat['losses'] for stat in data.values())
            if total_trades > 20:
                win_count = sum(stat['wins'] for stat in data.values())
                if (win_count / total_trades) < 0.3:
                    to_prune.append(combo)

        for combo in to_prune:
            del self.combination_performance[combo]
            self.group_bonus.pop(combo, None)

    def get_dynamic_combo_decay(self, phase, atr_value):
        base = settings.PHASE_DECAY_MAP.get(phase, 0.95)

        if atr_value > settings.COMBO_DECAY_ATR_HIGH_THRESHOLD:
            base -= settings.COMBO_DECAY_STRONG_REDUCTION
        elif atr_value < settings.COMBO_DECAY_ATR_LOW_THRESHOLD:
            base += settings.COMBO_DECAY_WEAK_BOOST

        return max(0.85, min(base, 0.98))
