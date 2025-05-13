# strategy_manager.py
import settings
from logic.fusion_engine import fuse_probabilities
from logic.meta_strategy_tuner import MetaStrategyTuner
from logic.meta_indicator_learning import MetaIndicatorLearning
from logic.market_phase_manager import MarketPhaseManager
from utils.runtime_optimizer import load_active_symbols, refresh_active_symbols
from execution.trade_manager import close_position_safely
from mt5_wrapper import is_position_open

class StrategyManager:
    def __init__(self, indicators=settings.DEFAULT_INDICATOR_WEIGHTS):
        self.indicators_by_symbol = {}
        self.default_weights = indicators.copy()
        self.meta_tuner = MetaStrategyTuner()
        self.meta_indicator_learning = MetaIndicatorLearning()
        self.market_phase_manager = MarketPhaseManager()
        self.active_symbols = load_active_symbols()  # Loaded once at init

    def evaluate_symbol(self, symbol, market_data):
        if symbol not in self.active_symbols:
            print(f"[StrategyManager] ⏭️ Skipping {symbol} — not in top 20.")
            return None

        # Inserisci qui la logica vera di valutazione, es. fusione
        confidence = self.meta_tuner.compute_confidence(symbol, market_data)
        return confidence
    
    def close_positions_outside_top20(self):
        all_symbols = get_all_open_symbols()  # Funzione che restituisce i simboli con posizioni aperte
        for symbol in all_symbols:
            if symbol not in self.active_symbols:
                print(f"[Bot] {symbol} fuori dalla top 20. Chiusura posizione.")
                close_position_safely(symbol)
                send_message(f"Posizione chiusa su {symbol} (fuori dalla top 20).")

    def get_weights(self, symbol):
        if symbol not in self.indicators_by_symbol:
            self.indicators_by_symbol[symbol] = self.default_weights.copy()
        return self.indicators_by_symbol[symbol]

    def calculate_signals(self, df, market_phase):
        signals = {}
        close = df['close'].iloc[-1]

        # Phase-based parameters
        phase_params = {
            'trending':     {'rsi': 60, 'macd_gap': 0.0, 'stoch': 20, 'cloud_clearance': 0.0},
            'ranging':      {'rsi': 50, 'macd_gap': 0.2, 'stoch': 30, 'cloud_clearance': 0.01},
            'volatile':     {'rsi': 40, 'macd_gap': 0.4, 'stoch': 40, 'cloud_clearance': 0.02},
        }
        p = phase_params.get(market_phase, phase_params['ranging'])

        if 'RSI' in df.columns:
            rsi = df['RSI'].iloc[-1]
            signals['RSI'] = 1 if rsi < p['rsi'] else 0

        if 'MACD' in df.columns and 'MACD_signal' in df.columns:
            macd_val = df['MACD'].iloc[-1]
            macd_signal = df['MACD_signal'].iloc[-1]
            signals['MACD'] = 1 if (macd_val - macd_signal) > p['macd_gap'] else 0

        if 'MA_50' in df.columns and 'MA_200' in df.columns:
            ma50 = df['MA_50'].iloc[-1]
            ma200 = df['MA_200'].iloc[-1]
            crossover_gap = abs(ma50 - ma200) / close
            signals['MA'] = 1 if (ma50 > ma200 and crossover_gap > 0.005) else 0

        if 'Stoch' in df.columns:
            stoch_val = df['Stoch'].iloc[-1]
            signals['Stochastic'] = 1 if stoch_val < p['stoch'] else 0

        if 'BBL' in df.columns and 'BBU' in df.columns:
            bbl = df['BBL'].iloc[-1]
            bbu = df['BBU'].iloc[-1]
            price = df['close'].iloc[-1]
            band_width = bbu - bbl
            pos = (price - bbl) / band_width if band_width else 0.5
            signals['BBands'] = pos

        if 'OBV' in df.columns:
            obv_slope = df['OBV'].diff().iloc[-1]
            signals['OBV'] = 1 if obv_slope > 0 else 0

        if 'SpanA' in df.columns and 'SpanB' in df.columns:
            span_a = df['SpanA'].iloc[-1]
            span_b = df['SpanB'].iloc[-1]
            cloud = max(span_a, span_b)
            clearance = (close - cloud) / close
            signals['Ichimoku'] = 1 if clearance > p['cloud_clearance'] else 0

        return signals

    def evaluate_position(self, symbol, signals, df, market_phase, lstm_pred, cnn_pred, sentiment):
        weights = self.get_weights(symbol)
        direction, confidence, final_prob, used_inds = fuse_probabilities(signals, lstm_pred, cnn_pred, sentiment, weights)
        return direction, confidence, final_prob, used_inds

    def update_weights(self, symbol, used_inds, pl_pct, phase, direction, atr_val):
        # --- Reward synergies between indicators ---
        self.meta_indicator_learning.reward_synergistic_combinations(
            self.indicators_by_symbol[symbol],
            used_inds,
            phase,
            direction,
            profit=pl_pct
        )

        # --- Track and tune phase-specific indicator performance ---
        self.meta_tuner.track_indicator_performance(
            phase, used_inds, pl_pct, atr_value=atr_val
        )

        self.meta_tuner.adjust_weights_by_phase(
            self.indicators_by_symbol[symbol], phase
        )

        # --- Track indicator combinations and learn ---
        self.meta_indicator_learning.track_combination(
            symbol, used_inds, pl_pct
        )