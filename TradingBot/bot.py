from __future__ import annotations

# — libreria standard — -------------------------------------------------
import time
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import csv
import threading
from os.path import exists

# — librerie di terze parti — ------------------------------------------
import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta

# — pacchetti interni — -------------------------------------------------
from TradingSystem.AutoManager.supervisor import (
    evaluate_patch_result_and_decide,
)
from TradingSystem.AutoManager.lock_manager import is_locked

from . import settings
from .utils.messaging import send_message
from .logic.strategy_manager import StrategyManager
from .execution.trade_manager import TradeManager
from .logic.market_phase_manager import MarketPhaseManager
from .logic.meta_indicator_learning import MetaIndicatorLearning
from .logic.meta_strategy_tuner import MetaStrategyTuner
from .logic.fusion_engine import fuse_probabilities
from .models.lstm_model import LSTMModel
from .models.cnn_model import CNNModel
from .models.modello_sett import SentimentModel
from .utils.plotter import plot_candlestick
from .utils.sentiment_fetcher import fetch_sentiment_for
from .utils.training_data_builder import build_from_symbol

# (se ti serve ancora la costante ROOT per leggere file di supporto,
#  puoi lasciarla, ma NON toccare sys.path)
ROOT = Path(__file__).resolve().parent.parent


class ForexTradingBot:
    def __init__(self, manual_multiplier=None, flip_cooldown_secs=None):
        if not mt5.initialize():
            raise ConnectionError("Failed to initialize MT5 connection")
        
        self.last_symbol_refresh = 0

        self.consecutive_failures = 0
        self.last_known_equity = self.get_balance()

        self.daily_pnl = 0.0
        self.daily_start_equity = self.get_balance()
        self.daily_loss_triggered = False
        self.last_reset_date = TradingSystem.TradingBot.datetime.now().date()


        account_info = mt5.account_info()
        self.balance = account_info.balance if account_info else .settings.DEFAULT_BALANCE

        self.positions = list(mt5.positions_get() or [])
        self.trade_manager.revalidate_stop_targets(self.positions)
        self.trade_log = [{"ticket": pos.ticket, "symbol": pos.symbol} for pos in self.positions]

        self.enable_trailing_stops = .settings.ENABLE_TRAILING_STOPS
        self.enable_partial_tp      = .settings.ENABLE_PARTIAL_TP
        self.enable_break_even      = .settings.ENABLE_BREAK_EVEN

        loaded_weights = self.load_indicator_weights()
        if loaded_weights:
            self.strategy_manager = StrategyManager(loaded_weights)
        else:
            self.strategy_manager = StrategyManager(.settings.DEFAULT_INDICATOR_WEIGHTS)

        self.trade_manager         = TradeManager(manual_multiplier or .settings.MANUAL_POSITION_MULTIPLIER)
        self.market_phase_manager  = MarketPhaseManager()
        self.meta_indicator_learning = MetaIndicatorLearning()
        self.meta_strategy_tuner     = MetaStrategyTuner()

        self.close_all_flag   = False
        self.listener_thread  = None

        self.symbols = .settings.SYMBOLS
        self.flip_cooldown_secs = flip_cooldown_secs or .settings.FLIP_COOLDOWN_SECONDS

        self.last_flip_bar  = {}
        self.last_direction = {}
        
        self.crash_once = True  # <-- crash flag

        # AI models
        self.lstm_models = {
            symbol: LSTMModel(.settings.LSTM_MODEL_PATH.format(symbol))
            for symbol in self.symbols
        }

        self.cnn_models = {
            symbol: CNNModel(.settings.CNN_MODEL_PATH.format(symbol))
            for symbol in self.symbols
        }

        self.sentiment_models = {
            symbol: SentimentModel(.settings.SENTIMENT_MODEL_NAME)
            for symbol in self.symbols
        }

    def load_indicator_weights(self):
        if TradingSystem.TradingBot.os.path.exists(.settings.INDICATOR_WEIGHTS_FILE):
            with open(.settings.INDICATOR_WEIGHTS_FILE, "r") as f:
                return TradingSystem.TradingBot.json.load(f)
        return None

    def save_indicator_weights(self):
        with open(.settings.INDICATOR_WEIGHTS_FILE, "w") as f:
            TradingSystem.TradingBot.json.dump(self.strategy_manager.indicators_by_symbol, f, indent=2)

    def get_performance_stats(self):
        path = .settings.TRADE_LOG_CSV
        if not TradingSystem.TradingBot.os.path.exists(path):
            print("No trade logs found.")
            return None

        df = pd.read_csv(path, parse_dates=["timestamp"])
        now = TradingSystem.TradingBot.datetime.now()

        def summarize(df_slice):
            wins = df_slice[df_slice["profit"] > 0]
            losses = df_slice[df_slice["profit"] <= 0]
            return {
                "trades": len(df_slice),
                "win_rate": round(len(wins) / len(df_slice) * 100, 2) if len(df_slice) > 0 else 0,
                "avg_profit": round(df_slice["profit"].mean(), 2) if not df_slice.empty else 0,
                "total_pnl": round(df_slice["profit"].sum(), 2)
            }

        stats_24h = summarize(df[df["timestamp"] > now - timedelta(days=1)])
        stats_7d  = summarize(df[df["timestamp"] > now - timedelta(days=7)])
        stats_30d = summarize(df[df["timestamp"] > now - timedelta(days=30)])

        summary = {
            "24h": stats_24h,
            "7d": stats_7d,
            "30d": stats_30d
        }

        print("\n📊 Performance Summary:")
        for period, s in summary.items():
            print(f"{period} :: Trades: {s['trades']}, Win Rate: {s['win_rate']}%, Avg Profit: {s['avg_profit']}, Total PnL: {s['total_pnl']}")

        return summary

    def get_balance(self):
        info = mt5.account_info()
        return info.balance if info else self.balance

    def is_market_closed(self, symbol):
        tick = mt5.symbol_info_tick(symbol)
        if not tick or tick.last == 0:
            return True  # No price data at all
        last_tick_time = TradingSystem.TradingBot.datetime.fromtimestamp(tick.TradingSystem.TradingBot.time)
        now = TradingSystem.TradingBot.datetime.now()
        diff = (now - last_tick_time).total_seconds()
        return diff > 300  # If no update in last 5 minutes, likely closed

    def log_event(self, message):
        timestamp = TradingSystem.TradingBot.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        with open(.settings.LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(log_message + "\n")
        print(log_message)

    def _input_listener(self):
        while True:
            cmd = input().strip().lower()
            if cmd == "close":
                self.log_event("🔴 Closing all positions...")
                self.close_all_positions()
                self.close_all_flag = True
                break
            elif cmd == "balance":
                self.log_event(f"💰 Current Balance: ${self.get_balance():,.2f}")
            elif cmd.startswith("mult "):
                try:
                    val = float(cmd.split(" ")[1])
                    self.trade_manager.set_manual_multiplier(val)
                    self.log_event(f"⚙️ Manual position multiplier set to {val:.2f}")
                except Exception:
                    self.log_event("⚠️ Invalid multiplier command.")
            elif cmd.startswith("retrain "):
                parts = cmd.split()
                if len(parts) == 3:
                    symbol = parts[1].upper()
                    path = parts[2]
                    from .utils.upload_retrainer import retrain_from_csv
  
                    success = retrain_from_csv(symbol, path)
                    if success:
                        self.log_event(f"✅ Manual retraining complete for {symbol} from {path}")
                    else:
                        self.log_event(f"❌ Failed to retrain {symbol} from {path}")
                else:
                    print("Usage: retrain SYMBOL /path/to/your.TradingSystem.TradingBot.csv")

    def close_positions_outside_top20(self):
        open_symbols = get_all_open_symbols()
        active_symbols = load_active_symbols()

        for symbol in open_symbols:
            if symbol not in active_symbols:
                print(f"[BOT] ❌ {symbol} fuori dalla top 20. Chiusura.")
                close_trade(symbol)
                send_message(f"🚫 Posizione chiusa su {symbol} — fuori dalla top 20.")

    def log_trade_result(self, trade, profit, pl_pct):
        log_path = .settings.TRADE_LOG_CSV
        file_exists = TradingSystem.TradingBot.os.path.isfile(log_path)

        with open(log_path, "a", newline="") as csvfile:
            fieldnames = ["timestamp", "symbol", "direction", "confidence", "entry", "size", "profit", "pl_pct"]
            writer = TradingSystem.TradingBot.csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow({
                "timestamp": TradingSystem.TradingBot.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": trade["symbol"],
                "direction": trade["direction"],
                "confidence": trade["confidence"],
                "entry": trade["entry"],
                "size": trade["size"],
                "profit": profit,
                "pl_pct": round(pl_pct, 2)
            })

    def close_all_positions(self):
        open_positions = mt5.positions_get()
        if not open_positions:
            self.log_event("No open positions to close.")
            return
        for pos in open_positions:
            self.trade_manager.close_trade(pos.ticket)
        self.log_event("All positions closed.")

    def fetch_data_mt(self, symbol, timeframe, bars):
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None or (hasattr(rates, '__len__') and len(rates) == 0):
                print(f"[ERROR] No data received for {symbol} @ timeframe {timeframe}")
                return None
        df = pd.DataFrame(rates)
        df['TradingSystem.TradingBot.time'] = pd.to_datetime(df['TradingSystem.TradingBot.time'], unit='s')
        return df    

    def fetch_multiple_timeframes(self, symbol):
        """
        If MULTI_TIMEFRAME_ENABLED is True, fetch data for all timeframes in .settings.MULTI_TIMEFRAME_LIST.
        Returns a dict with keys being the timeframe labels and values the corresponding DataFrames.
        Otherwise, returns a dict with just the default M5 data.
        """
        tf_label = .settings.EXECUTION_TF_LABEL
        tf_constant = next((code for code, label in .settings.MULTI_TIMEFRAME_LIST if label == tf_label), mt5.TIMEFRAME_M5)
        df_single = self.fetch_data_mt(symbol, tf_constant, .settings.BAR_COUNT)
        return {tf_label: df_single}

        timeframe_data = {}
        count = 0
        for (tf_constant, label) in .settings.MULTI_TIMEFRAME_LIST:
            if count >= .settings.MAX_TIMEFRAMES:
                break
            df_tf = self.fetch_data_mt(symbol, tf_constant, .settings.BAR_COUNT)
            timeframe_data[label] = df_tf
            count += 1
        return timeframe_data

    def allowed_to_flip_direction(self, symbol, new_direction, df, market_phase):
        if symbol not in self.last_direction:
            return True
        old_direction = self.last_direction[symbol]
        if new_direction == old_direction:
            return True

        last_bar = self.last_flip_bar.get(symbol, None)
        if last_bar is None:
            return True

        mask = df['TradingSystem.TradingBot.time'] > last_bar
        passed_candles = mask.sum()
        needed_candles = .settings.PHASE_BASED_FLIP_COOLDOWN_CANDLES.get(market_phase, 3)
        if passed_candles < needed_candles:
            self.log_event(f"Flip cooldown not met for {symbol}. Passed={passed_candles}, needed={needed_candles}.")
            return False
        return True

    def run(self):
        self.log_event("Bot started.")
        self.listener_thread = TradingSystem.TradingBot.threading.Thread(target=self._input_listener, daemon=True)
        self.listener_thread.start()

        now = TradingSystem.TradingBot.time.TradingSystem.TradingBot.time()
        if now - self.last_symbol_refresh >= 3600:  # ogni ora
            self.strategy_manager.refresh_active_symbols()
            self.close_positions_outside_top20()
            self.last_symbol_refresh = now
            
        try:
            while not self.close_all_flag:
                if self.crash_once:
                    self.crash_once = False
                    raise ValueError("🔥 Simulated crash for GPT test")
                
                self.check_closed_positions()
                self.manage_open_positions()
                symbol_sentiment_scores = {}
                
                if self.daily_loss_triggered:
                    self.log_event("⛔ Daily loss limit active. Skipping trade attempts.")
                    TradingSystem.TradingBot.time.sleep(1)
                    continue


                for symbol in self.symbols:
                    # Step 1: Auto-generate model if missing
                    lstm_path = f"models/{symbol}_lstm_model.h5"
                    cnn_path = f"models/{symbol}_cnn_model.h5"

                    if not exists(lstm_path) or not exists(cnn_path):
                        self.log_event(f"🛠️ Bootstrapping new symbol: {symbol}")

                            # Build and enrich data if needed
                        try:
                            build_from_symbol(symbol, timeframes=[.settings.EXECUTION_TF_LABEL, .settings.EXECUTION_TF_LABEL, .settings.EXECUTION_TF_LABEL])
                        except Exception as e:
                            self.log_event(f"❌ Failed to build data for {symbol}: {e}")
                            continue

                        try:
                            self.lstm_model.retrain(symbol)
                            self.cnn_model.retrain(symbol)
                        except Exception as e:
                            self.log_event(f"❌ Failed to train model for {symbol}: {e}")
                            continue


                    if self.is_market_closed(symbol):
                        self.log_event(f"⏸️ Market appears closed for {symbol}. Skipping.")
                        continue
                    tf_data = self.fetch_multiple_timeframes(symbol)
                    exec_label = .settings.EXECUTION_TF_LABEL
                    df = tf_data.get(exec_label, pd.DataFrame())

                    if df is None or df.empty:
                        print(f"[WARN] No usable {.settings.EXECUTION_TF_LABEL} data for {symbol}, skipping.")

                        continue   
                    # For classical indicators, we use M5 data
                    if df.empty:
                        continue
                    sentiment = symbol_sentiment_scores.get(symbol, 0.0)

                    short_ma = df['MA_50'].iloc[-1] if 'MA_50' in df.columns else ta.sma(df['close'], length=50).iloc[-1]
                    long_ma  = df['MA_200'].iloc[-1] if 'MA_200' in df.columns else ta.sma(df['close'], length=200).iloc[-1]
                    atr      = df['ATR'].iloc[-1] if 'ATR' in df.columns else ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]

                    market_phase = self.market_phase_manager.detect_phase_for_symbol(
                        symbol, df['close'], short_ma, long_ma, atr
                    )

                    signals = self.strategy_manager.calculate_signals(df, market_phase)

                    # Multi-timeframe predictions for AI models:
                    if .settings.MULTI_TIMEFRAME_ENABLED:
                        df_m5  = tf_data.get(.settings.EXECUTION_TF_LABEL, pd.DataFrame())
                        df_m15 = tf_data.get(.settings.EXECUTION_TF_LABEL, pd.DataFrame())
                        df_h1  = tf_data.get(.settings.EXECUTION_TF_LABEL, pd.DataFrame())
                        # Use multi-timeframe prediction methods if available.
                        lstm_pred = self.lstm_models[symbol].predict_multi_timeframe(df_m5, df_m15, df_h1)
                        cnn_pred = self.cnn_models[symbol].predict_multi_timeframe(df_m5, df_m15, df_h1)
                    else:
                        lstm_pred = self.lstm_model.predict_direction(df)
                        cnn_pattern = self.cnn_model.predict_pattern(df)

                    sentiment_score = self.sentiment_models[symbol].score(latest_news_text)

                    from .utils.indicator_analysis import learn_indicator_combos
  

                    # Learn indicator combo performance dynamically
                    top_combos = learn_indicator_combos(symbol)

                    # Convert predictions to fusion-ready scores
                    lstm_score = 1.0 if lstm_pred == 1 else -1.0 if lstm_pred == -1 else 0.0
                    cnn_score = 1.0 if cnn_pattern == "double_bottom" else -1.0 if cnn_pattern == "head_and_shoulders" else 0.0
                    classical_score = 1.0 if signals.get("buy") else -1.0 if signals.get("sell") else 0.0

                    # Fuse it all together
                    fused_direction = fuse_probabilities(
                        lstm_score=lstm_score,
                        cnn_score=cnn_score,
                        sentiment_score=sentiment_score,
                        classical_score=classical_score
                    )

                    # Translate to direction
                    if fused_direction == 1:
                        direction = 'long'
                    elif fused_direction == -1:
                        direction = 'short'
                    else:
                        direction = 'hold'

                    # Confidence = average absolute strength
                    confidence = abs(lstm_score + cnn_score + sentiment_score + classical_score) / 4
                    used_inds = ["lstm", "cnn", "sentiment", "classical"]

                    combo_key = tuple(sorted(used_inds))
                    if combo_key in top_combos and top_combos[combo_key] > 0:
                        self.log_event(f"🔥 Combo {combo_key} has avg PnL {top_combos[combo_key]:.2f} — boosting confidence")
                        confidence *= 1.1

                    #  Now place your message block here:
                    if confidence > 0.6 or direction != 'hold':
                        send_message(
                            f"📊 *{symbol}*\n"
                            f"LSTM: `{lstm_score:.2f}` | CNN: `{cnn_score:.2f}`\n"
                            f"Sentiment: `{sentiment_score:.2f}` | Classical: `{classical_score:.2f}`\n"
                            f"📈 *Direction:* `{direction}` | *Confidence:* `{confidence:.2f}`"
                        )


                    combo_key = tuple(sorted(used_inds))
                    if combo_key in top_combos and top_combos[combo_key] > 0:
                        self.log_event(f"🔥 Combo {combo_key} has avg PnL {top_combos[combo_key]:.2f} — boosting confidence")
                        confidence *= 1.1  # or adjust based on PnL magnitude
                    final_prob = confidence

                    self.log_event(f"Symbol: {symbol}, Decision: {direction}, Confidence: {confidence:.2f}")

                    if direction == 'hold':
                        continue

                    can_flip = self.allowed_to_flip_direction(symbol, direction, df, market_phase)
                    if not can_flip:
                        continue

                    symbol_info_tick = mt5.symbol_info_tick(symbol)
                    if not symbol_info_tick:
                        continue

                    entry_price = symbol_info_tick.ask if direction == 'long' else symbol_info_tick.bid
                    sl_price = entry_price - (.settings.ATR_MULTIPLIER) if direction == 'long' else entry_price + (.settings.ATR_MULTIPLIER)
                    lot_size = self.trade_manager.calculate_position_size(
                        balance=self.get_balance(),
                        symbol=symbol,
                        entry_price=entry_price,
                        sl_price=sl_price,
                        risk_percent=.settings.RISK_PERCENT,
                        confidence=confidence
                    )
                    trade_result = self.trade_manager.execute_trade(
                        symbol, direction, entry_price, atr, lot_size, confidence
                    )
                    self.trade_manager.update_trailing_stop(symbol)
                    if trade_result is not None:
                        last_df_time = df['TradingSystem.TradingBot.time'].iloc[-1]
                        self.last_flip_bar[symbol] = last_df_time
                        self.last_direction[symbol] = direction

                        trade_result['used_indicators'] = used_inds
                        trade_result['phase'] = market_phase
                        trade_result['symbol'] = symbol
                        trade_result['atr'] = atr
                        trade_result['confidence'] = confidence
                        trade_result['direction'] = direction
                        trade_result['entry'] = entry_price
                        trade_result['sl'] = sl_price
                        trade_result['size'] = lot_size
                        trade_result['opened_bar'] = last_df_time

                        self.positions.append(trade_result)
                        self.log_event(f"Opened trade: {trade_result}")

                self.save_indicator_weights()
                self.log_event("Cycle complete, waiting for next iteration.")

                if self.consecutive_failures >= .settings.MAX_CONSECUTIVE_FAILURES:
                    self.log_event("🚨 Max consecutive trade failures reached!")
                    send_message("🚨 Max consecutive trade failures reached!")
        
                current_equity = self.get_balance()
                if current_equity < .settings.EQUITY_ALERT_THRESHOLD and self.last_known_equity >= .settings.EQUITY_ALERT_THRESHOLD:
                    self.log_event(f"🚨 Equity dropped below threshold! Current: ${current_equity:.2f}")
                    # 🔔 TODO: Add Telegram alert here
                    send_message(f"🚨 Equity dropped below threshold! Current: ${current_equity:.2f}")

                self.last_known_equity = current_equity
                # Patch testing eval
                # Patch testing eval
                if settings_manager.FULL_PRODUCTION_MODE:
                    try:
                        from TradingSystem.AutoManager.supervisor import evaluate_patch_result_and_decide
                        evaluate_patch_result_and_decide(
                            winrate=bot_stats.get("winrate", 1.0),
                            drawdown=bot_stats.get("max_drawdown", 0.0),
                            profit=bot_stats.get("daily_profit", 0.0),
                            precision=bot_stats.get("precision", 1.0)
                        )
                    except Exception as e:
                        self.log_event(f"[PatchEval] Errore valutazione patch: {e}")
                TradingSystem.TradingBot.time.sleep(.settings.LOOP_INTERVAL_SECONDS)

        finally:
            mt5.shutdown()
            self.save_indicator_weights()
            self.log_event("Bot shutdown.")

    def check_closed_positions(self):
        open_tickets = {pos.ticket for pos in mt5.positions_get()}
        still_open = []
        for trade in self.positions:
            if trade['ticket'] not in open_tickets:
                deals = mt5.history_deals_get(ticket=trade['ticket'])
                if deals:
                    net_profit = sum(d.profit for d in deals if d.ticket == trade['ticket'])
                    nominal_cost = trade['entry'] * trade['size']
                    pl_pct = (net_profit / nominal_cost) * 100 if nominal_cost != 0 else 0
                else:
                    pl_pct = 0
                self.log_trade_result(trade, profit=net_profit, pl_pct=pl_pct)
                self.log_event(f"Trade {trade['ticket']} closed with P/L%: {pl_pct:.2f}")
                self.daily_pnl += net_profit

                # Reset daily stats if a new day has started
                if TradingSystem.TradingBot.datetime.now().date() != self.last_reset_date:
                    self.daily_pnl = 0.0
                    self.daily_start_equity = self.get_balance()
                    self.last_reset_date = TradingSystem.TradingBot.datetime.now().date()
                    self.daily_loss_triggered = False

                # Trigger auto-disable if loss exceeds threshold
                if not self.daily_loss_triggered:
                    loss_pct = (self.daily_pnl / self.daily_start_equity) * 100
                    if loss_pct <= -.settings.DAILY_LOSS_LIMIT_PCT:
                        self.log_event(f"🚨 Daily loss limit hit! Net PnL: {loss_pct:.2f}% — disabling trades.")
                        send_message(f"🚨 Bot disabled due to daily loss limit ({loss_pct:.2f}%)")
                        self.daily_loss_triggered = True

                self.strategy_manager.update_weights(
                    trade['symbol'],
                    used_indicators=trade['used_indicators'],
                    pl_pct=pl_pct,
                    phase=trade['phase'],
                    direction=trade['direction'],
                    atr_val=trade.get('atr', 1.0)
                )
                self.trigger_background_retraining(trade["symbol"])
            else:
                still_open.append(trade)
        self.positions = still_open

    def manage_open_positions(self):
        if not self.positions:
            return
        mt5_positions = {p.ticket: p for p in mt5.positions_get()}
        for trade in self.positions:
            ticket = trade['ticket']
            if ticket not in mt5_positions:
                continue

            current_pos = mt5_positions[ticket]
            symbol = trade['symbol']
            direction = trade['direction']
            phase = trade['phase']
            confidence = trade['confidence']
            atr = trade['atr']
            entry_price = trade['entry']
            lot_size = trade['size']
            current_sl = current_pos.sl
            current_tp = current_pos.tp
            current_price = mt5.symbol_info_tick(symbol).bid if direction == 'long' else mt5.symbol_info_tick(symbol).ask

            # Trailing stops
            if self.enable_trailing_stops:
                tc = .settings.TRAILING_CONFIG.get(phase, {"base_stop_factor":2.0, "confidence_boost":0.0})
                ts_factor = tc['base_stop_factor']
                if confidence > 0.7:
                    ts_factor += tc['confidence_boost']
                if direction == 'long':
                    desired_sl = current_price - (atr * ts_factor)
                    if desired_sl > current_sl:
                        self.log_event(f"Updating trailing stop for ticket {ticket}. Old SL={current_sl}, New SL={desired_sl:.5f}")
                        self.update_sl(ticket, desired_sl)
                else:
                    desired_sl = current_price + (atr * ts_factor)
                    if desired_sl < current_sl or current_sl <= 0:
                        self.log_event(f"Updating trailing stop for ticket {ticket}. Old SL={current_sl}, New SL={desired_sl:.5f}")
                        self.update_sl(ticket, desired_sl)

            # Partial TPs
            if self.enable_partial_tp:
                ptc = .settings.PARTIAL_TP_CONFIG.get(phase, {"tp_factor":2.0, "confidence_boost":0.0, "partial_close_ratio":0.5})
                tp_factor = ptc['tp_factor']
                if confidence > 0.7:
                    tp_factor += ptc['confidence_boost']
                if direction == 'long':
                    gain = current_price - entry_price
                    if gain >= (atr * tp_factor):
                        ratio = ptc['partial_close_ratio']
                        partial_lots = lot_size * ratio
                        if partial_lots >= 0.01:
                            self.log_event(f"Taking partial TP on ticket {ticket}. Gains ~ {gain:.5f} => closing {partial_lots} lots.")
                            self.partial_close_trade(ticket, partial_lots)
                else:
                    gain = entry_price - current_price
                    if gain >= (atr * tp_factor):
                        ratio = ptc['partial_close_ratio']
                        partial_lots = lot_size * ratio
                        if partial_lots >= 0.01:
                            self.log_event(f"Taking partial TP on ticket {ticket}. Gains ~ {gain:.5f} => closing {partial_lots} lots.")
                            self.partial_close_trade(ticket, partial_lots)

            # Break-even stops
            if self.enable_break_even:
                bec = .settings.BREAK_EVEN_CONFIG.get(phase, {"be_factor":1.5, "confidence_boost":0.5})
                be_factor = bec['be_factor']
                if confidence > 0.7:
                    be_factor += bec['confidence_boost']
                if direction == 'long':
                    if (current_price - entry_price) >= (atr * be_factor):
                        if current_sl < entry_price:
                            self.log_event(f"Moving SL to break-even for ticket {ticket}. Old SL={current_sl}, BE={entry_price}")
                            self.update_sl(ticket, entry_price)
                else:
                    if (entry_price - current_price) >= (atr * be_factor):
                        if current_sl == 0 or current_sl > entry_price:
                            self.log_event(f"Moving SL to break-even for ticket {ticket}. Old SL={current_sl}, BE={entry_price}")
                            self.update_sl(ticket, entry_price)

    def update_sl(self, ticket, new_sl):
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            self.log_event(f"Cannot update SL: no open position for ticket {ticket}.")
            return
        symbol = pos[0].symbol
        direction = pos[0].type
        volume = pos[0].volume
        price = mt5.symbol_info_tick(symbol).bid if direction == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "sl": new_sl,
            "tp": pos[0].tp,
            "price": price,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "deviation": 10,
            "magic": 123456,
            "comment": "Update SL",
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.log_event(f"SL update failed for ticket {ticket}: {result.comment}")
        else:
            self.log_event(f"SL updated successfully for ticket {ticket}.")

    def trigger_background_retraining(self, symbol):
        def retrain_task():
            self.log_event(f"🧠 Starting background retraining for {symbol}...")
            try:
                self.lstm_models[symbol].retrain(symbol)
                self.log_event(f"✅ Retraining complete for {symbol}.")
            except Exception as e:
                self.log_event(f"❌ Retraining failed for {symbol}: {e}")

        TradingSystem.TradingBot.threading.Thread(target=retrain_task, daemon=True).start()

    def partial_close_trade(self, ticket, close_lots):
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            self.log_event(f"Partial close failed: no position for ticket {ticket}.")
            return
        symbol = pos[0].symbol
        volume = pos[0].volume
        if close_lots > volume:
            close_lots = volume
        
        from .settings import MIN_LOT_SIZE
  

        if close_lots < MIN_LOT_SIZE:
            self.log_event(f"Partial close skipped: {close_lots} below MIN_LOT_SIZE.")
            return

        direction = mt5.ORDER_TYPE_SELL if pos[0].type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if direction == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": close_lots,
            "type": direction,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": 123456,
            "comment": "Partial TP",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.log_event(f"Partial close failed: {result.comment}")
        else:
            self.log_event(f"Closed {close_lots} lots from ticket {ticket}.")

def main():
    print("Main originale del bot.")