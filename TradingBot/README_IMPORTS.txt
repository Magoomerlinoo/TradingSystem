📘 INTEGRATION INSTRUCTIONS

This project has been upgraded to include:

✅ Real-time Telegram control (/pause, /resume, /risk, /mode, etc.)
✅ Confidence-based position sizing
✅ Normalized decision logic (fuse_probabilities)
✅ Clean folder structure with runtime logs, signals, and trades

📁 Key Files:
- telegram/telegram_bot.py: Handles all Telegram commands and live updates to settings.py
- logic/fusion_engine.py: Updated signal fusion logic with directional score
- execution/trade_manager.py: Updated with dynamic position sizing
- settings.py: All key variables now persist and respond to Telegram
- main.py: Include telegram listener thread using the provided snippet

📂 Runtime Folders:
- runtime/logs: All logs go here
- runtime/signals: Includes close_all.txt for manual closures
- runtime/trades: Executed trade logs

To embed the Telegram listener:
-------------------------------
import threading
import telegram.telegram_bot as telegram_bot

def run_telegram():
    telegram_bot.bot.infinity_polling()

threading.Thread(target=run_telegram, daemon=True).start()