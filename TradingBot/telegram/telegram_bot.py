import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import telebot
import settings
import importlib
from datetime import datetime
from bot import ForexTradingBot
from utils.sentiment_fetcher import fetch_sentiment_for
import settings
from logic.fusion_engine import fuse_probabilities

bot = telebot.TeleBot(settings.TELEGRAM_TOKEN)
bot_instance = ForexTradingBot()

def send_message(msg):
    bot.send_message(settings.TELEGRAM_CHAT_ID, msg, parse_mode="Markdown")

# Reload settings and update file
def update_settings_file(key, value, is_string=False):
    path = "settings.py"
    with open(path, "r") as f:
        lines = f.readlines()

    new_lines = []
    updated = False
    for line in lines:
        if line.strip().startswith(f"{key}"):
            new_line = f"{key} = \"{value}\"\n" if is_string else f"{key} = {value}\n"
            new_lines.append(new_line)
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"{key} = {value}\n")

    with open(path, "w") as f:
        f.writelines(new_lines)

    importlib.reload(settings)
        
# /risk command
@bot.message_handler(commands=['risk'])
def set_risk(message):
    try:
        value = float(message.text.split()[1])
        update_settings_file("RISK_PERCENT", value)
        send_message(f"Risk percent updated to {value}")
    except Exception:
        send_message("Usage: /risk 0.01")

# /multiplier command
@bot.message_handler(commands=['multiplier'])
def set_multiplier(message):
    try:
        value = float(message.text.split()[1])
        update_settings_file("MANUAL_POSITION_MULTIPLIER", value)
        send_message(f"Multiplier updated to {value}")
    except Exception:
        send_message("Usage: /multiplier 1.5")

# /mode command
@bot.message_handler(commands=['mode'])
def set_mode(message):
    try:
        mode = message.text.split()[1].strip().lower()
        if mode not in ["normal", "conservative"]:
            raise ValueError("Invalid mode")
        update_settings_file("STRATEGY_MODE", mode, is_string=True)
        send_message(f"Strategy mode updated to `{mode}`")
    except Exception:
        send_message("Usage: /mode normal OR /mode conservative")

# /status command
@bot.message_handler(commands=['status'])
def show_status(message):
    status = (
        f"*Bot Status:*\n"
        f"- Risk: `{settings.RISK_PERCENT}`\n"
        f"- Multiplier: `{settings.MANUAL_POSITION_MULTIPLIER}`\n"
        f"- Mode: `{getattr(settings, 'STRATEGY_MODE', 'normal')}`\n"
    )
    send_message(status)

# /performance command
@bot.message_handler(commands=['performance'])
def performance_command(message):
    try:
        stats = bot_instance.get_performance_stats()
        if not stats:
            send_message("No performance data available.")
            return

        s24 = stats["24h"]
        s7d = stats["7d"]
        s30 = stats["30d"]

        msg = (
            f"*Performance Summary*\n\n"
            f"*Last 24h:*\n"
            f"Trades: `{s24['trades']}` | Win Rate: `{s24['win_rate']}%`\n"
            f"Avg PnL: `{s24['avg_profit']}` | Total PnL: `{s24['total_pnl']}`\n\n"
            f"*Last 7d:*\n"
            f"Trades: `{s7d['trades']}` | Win Rate: `{s7d['win_rate']}%`\n"
            f"Avg PnL: `{s7d['avg_profit']}` | Total PnL: `{s7d['total_pnl']}`\n\n"
            f"*Last 30d:*\n"
            f"Trades: `{s30['trades']}` | Win Rate: `{s30['win_rate']}%`\n"
            f"Avg PnL: `{s30['avg_profit']}` | Total PnL: `{s30['total_pnl']}`"
        )
        send_message(msg)

    except Exception as e:
        send_message(f"Error: {e}")

# /shutdown command
@bot.message_handler(commands=['shutdown'])
def shutdown_bot(message):
    bot_instance.close_all_flag = True
    send_message("Bot shutdown signal sent. Use `/status` to confirm.")

@bot.message_handler(commands=['sentiment'])
def sentiment_command(message):
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            send_message("Usage: /sentiment EURUSD")
            return

        symbol = parts[1].upper()
        from utils.sentiment_fetcher import fetch_sentiment_for
        score = fetch_sentiment_for(symbol)
        send_message(f"Sentiment for *{symbol}*: `{score:.2f}`")

    except Exception as e:
        send_message(f"Error fetching sentiment: {e}")

@bot.message_handler(commands=['expand'])
def expand_command(message):
    try:
        bot.send_message(settings.TELEGRAM_CHAT_ID, """
    *Telegram Command Reference*

    *Bot Control*
/shutdown — Stops the bot and closes all trades.
/pause — Pauses new trade entries.
/resume — Resumes trading after a pause.
/restart — Restarts the bot (watchdog needed).
/refresh_models — Reloads models from disk.

    *Monitoring & Stats*
/status — Bot status, equity, pause state.
/equity — Shows current equity and margin.
/performance — Win rate, avg PnL over time.
/drawdown — Max drawdown since last restart.
/daily_pnl — PnL for today in % and dollars.
/open_trades — Lists all open trades.
/log 10 — Last 10 lines of bot logs.

    *Risk & Strategy*
/risk 0.01 — Set risk to 1% per trade.
/mode conservative — Switch bot mode.
/flipcooldown 300 — Flip cooldown in seconds.
/thresholds 0.4 0.6 — Update short/long thresholds.
/trailconfig trend_up 2.0 — Trailing SL for phase.
/riskmode on|off — Enable or disable daily loss SL.
/confidence_boost on|off — Toggle confidence boosting.

    *Model & Sentiment*
/sentiment EURUSD — Sentiment score for symbol.
/retrain EURUSD — Retrain LSTM + CNN.
/rebuild EURUSD — Regenerate CSVs and retrain.
/weights EURUSD — Show indicator weights.
/combo EURUSD — Show best-performing combos.

    *Alerts & Debug*
/alerts on|off — Toggle Telegram alerts.
/health — Bot ping check.
/ping — Test bot response.
/reload_settings — Reload settings.py live.
/eval 2 + 2 — Evaluate Python expression (dev only).
""", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(settings.TELEGRAM_CHAT_ID, f"Failed to show command list: {e}")

# === /pause ===
@bot.message_handler(commands=['pause'])
def pause_bot(message):
    bot_instance.pause_trading = True
    send_message("Trading paused. Open trades will continue to be managed.")

# === /resume ===
@bot.message_handler(commands=['resume'])
def resume_bot(message):
    bot_instance.pause_trading = False
    send_message("Trading resumed.")

# === /restart ===
@bot.message_handler(commands=['restart'])
def restart_bot(message):
    send_message("Restarting bot...")
    import os
    os._exit(1)

# === /refresh_models ===
@bot.message_handler(commands=['refresh_models'])
def refresh_models(message):
    try:
        bot_instance.lstm_model = LSTMModel(settings.LSTM_MODEL_PATH)
        bot_instance.cnn_model = CNNModel(settings.CNN_MODEL_PATH)
        send_message("Models reloaded from disk.")
    except Exception as e:
        send_message(f"Failed to reload models: {e}")

# === /status ===
@bot.message_handler(commands=['status'])
def show_status(message):
    status = (
        f"*Bot Status:*\n"
        f"- Risk: `{settings.RISK_PERCENT}`\n"
        f"- Multiplier: `{settings.MANUAL_POSITION_MULTIPLIER}`\n"
        f"- Mode: `{getattr(settings, 'STRATEGY_MODE', 'normal')}`\n"
    )
    send_message(status)

# === /drawdown ===
@bot.message_handler(commands=['drawdown'])
def drawdown(message):
    dd = getattr(bot_instance, 'max_drawdown', 'Not tracked')
    send_message(f"Max Drawdown: {dd}")

# === /open_trades ===
@bot.message_handler(commands=['open_trades'])
def open_trades(message):
    positions = mt5.positions_get()
    if not positions:
        send_message("No open trades.")
        return
    summary = "\n".join([f"{p.symbol} | {p.volume} lots | {'BUY' if p.type==0 else 'SELL'} @ {p.price_open}" for p in positions])
    send_message(f"Open Trades:\n{summary}")

# === /flipcooldown ===
@bot.message_handler(commands=['flipcooldown'])
def flipcooldown(message):
    try:
        value = int(message.text.split()[1])
        update_settings_file("FLIP_COOLDOWN_SECONDS", value)
        send_message(f"Flip cooldown updated to {value} seconds.")
    except:
        send_message("Usage: /flipcooldown 300")

# === /thresholds ===
@bot.message_handler(commands=['thresholds'])
def update_thresholds(message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 3:
            send_message("Uso corretto: /thresholds <SHORT_THRESHOLD> <LONG_THRESHOLD>")
            return

        short_thres = float(parts[1])
        long_thres = float(parts[2])

        update_settings_file("SHORT_THRESHOLD", short_thres)
        update_settings_file("LONG_THRESHOLD", long_thres)

        send_message(f"Thresholds aggiornati:\n- SHORT: `{short_thres}`\n- LONG: `{long_thres}`")
    except Exception as e:
        send_message(f"Errore durante l'aggiornamento: {e}")

# === /trailconfig ===
@bot.message_handler(commands=['trailconfig'])
def trailconfig(message):
    try:
        parts = message.text.split()
        phase = parts[1]
        value = float(parts[2])
        settings.TRAILING_CONFIG[phase]['base_stop_factor'] = value
        send_message(f"Trailing config updated for {phase} to {value}")
    except:
        send_message("Usage: /trailconfig trend_up 2.0")

# === /riskmode ===
@bot.message_handler(commands=['riskmode'])
def riskmode_toggle(message):
    try:
            parts = message.text.strip().split()
            if len(parts) != 2 or parts[1].lower() not in ["on", "off"]:
                send_message("Uso corretto: /daily_limit on/off")
                return

            mode = parts[1].lower()
            update_settings_file("ENABLE_DAILY_LOSS_LIMIT", mode == "on")
            send_message(f"Daily loss limit {'abilitato' if mode == 'on' else 'disabilitato'}")
    except Exception as e:
            send_message(f"Errore: {e}")

# === /confidence_boost ===
@bot.message_handler(commands=['confidence_boost'])
def toggle_boost(message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2 or parts[1].lower() not in ["on", "off"]:
            send_message("Uso corretto: /confidence_boost on|off")
            return

        mode = parts[1].lower()
        update_settings_file("ENABLE_COMBO_CONFIDENCE_BOOST", mode == "on")
        send_message(f"Combo boost {'abilitato' if mode == 'on' else 'disabilitato'}.")
    except Exception as e:
        send_message(f"Errore: {e}")

# === /retrain ===
@bot.message_handler(commands=['retrain'])
def retrain_model(message):
    try:
        symbol = message.text.split()[1].upper()
        bot_instance.lstm_model.retrain(symbol)
        bot_instance.cnn_model.retrain(symbol)
        send_message(f"Retraining triggered for {symbol}")
    except Exception as e:
        send_message(f"Retrain failed: {e}")

# === /rebuild ===
@bot.message_handler(commands=['rebuild'])
def rebuild(message):
    try:
        symbol = message.text.split()[1].upper()
        from utils.training_data_builder import build_from_symbol
        build_from_symbol(symbol)
        bot_instance.lstm_model.retrain(symbol)
        bot_instance.cnn_model.retrain(symbol)
        send_message(f"Rebuilt data and retrained for {symbol}")
    except Exception as e:
        send_message(f"Rebuild failed: {e}")

# === /weights ===
@bot.message_handler(commands=['weights'])
def weights(message):
    symbol = message.text.split()[1].upper()
    weights = bot_instance.strategy_manager.indicators_by_symbol.get(symbol, {})
    send_message(f"Weights for {symbol}:\n{weights}")

# === /combo ===
@bot.message_handler(commands=['combo'])
def combo(message):
    from utils.indicator_analysis import learn_indicator_combos
    symbol = message.text.split()[1].upper()
    combos = learn_indicator_combos(symbol)
    output = "\n".join([f"{combo}: {pnl:.2f}" for combo, pnl in combos.items()])
    send_message(f"Top combos for {symbol}:\n{output}")

# === /alerts ===
@bot.message_handler(commands=['alerts'])
def alerts_toggle(message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2 or parts[1].lower() not in ["on", "off"]:
            send_message("Uso corretto: /alerts on|off")
            return

        mode = parts[1].lower()
        update_settings_file("ALERTS_ENABLED", mode == "on")
        send_message(f"Alerts {'enabled' if mode == 'on' else 'disabled'}.")
    except Exception as e:
        send_message(f"Errore nella modifica degli alert: {e}")

# === /health ===
@bot.message_handler(commands=['health'])
def health(message):
    send_message("Bot is alive and responding.")

# === /ping ===
@bot.message_handler(commands=['ping'])
def ping(message):
    send_message("Pong!")

# === /eval ===
@bot.message_handler(commands=['eval'])
def eval_cmd(message):
    try:
        expr = message.text[len("/eval "):]
        result = eval(expr)
        send_message(f"Eval result: {result}")
    except Exception as e:
        send_message(f"Eval failed: {e}")

@bot.message_handler(commands=['execution_tf'])
def set_execution_tf(message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            send_message("Usage: /execution_tf M5 (or M15, H1, etc.)")
            return

        new_tf = parts[1].upper()

        # Validate if the label exists in the configured MULTI_TIMEFRAME_LIST
        valid_labels = [label for _, label in settings.MULTI_TIMEFRAME_LIST]
        if new_tf not in valid_labels:
            send_message(f"Invalid label: {new_tf}. Must be one of: {', '.join(valid_labels)}")
            return

        update_settings_file("EXECUTION_TF_LABEL", f'"{new_tf}"', is_string=True)
        send_message(f"Execution timeframe set to *{new_tf}*")

    except Exception as e:
        send_message(f"Failed to update execution TF: {e}")

# Start listening for commands
if __name__ == "__main__":
    send_message("Telegram bot started and ready to receive commands.")
    bot.infinity_polling()