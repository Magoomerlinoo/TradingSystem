
# 🧠 Forex Trading Bot (Fully Integrated)

This project is an intelligent, Telegram-controlled Forex trading bot.  
It uses a hybrid strategy powered by:
- LSTM/CNN models
- Sentiment analysis
- ATR-based dynamic SL/TP
- Market phase detection
- And full Telegram command control.

---

## 🚀 How to Run

```bash
python run.py
```

Ensure your settings and models are in place. The bot will check if the market is open, load its last state, and start trading if allowed.

---

## 🛠 Structure Overview

| Folder           | Purpose                                  |
|------------------|-------------------------------------------|
| `execution/`     | TradeManager and execution logic          |
| `logic/`         | Strategy fusion and SL/TP engine          |
| `models/`        | LSTM/CNN/Sentiment prediction logic       |
| `utils/`         | Logging, plotting, indicators             |
| `config/`        | Persistent state, holidays list, settings |
| `logs/`          | Restart logs and system output            |

---

## 🔐 Config

### Telegram Setup (in `settings.py`)
```python
TELEGRAM_BOT_TOKEN = "your_token"
TELEGRAM_CHAT_ID = "your_chat_id"
TELEGRAM_NOTIFY_ON_RESTART = True
```

### State & Holiday Control
- `config/state.json` → remembers if the bot is stopped and its trading mode
- `config/holidays.txt` → list of YYYY-MM-DD dates when the bot must stay inactive

---

## 💬 Telegram Commands

| Command         | Description |
|-----------------|-------------|
| `start`         | Activates bot (if previously stopped) |
| `stop`          | Closes all open positions and halts trading |
| `update`        | Shows stats from last 24h: trade count, win/loss, PnL, balance |
| `positions`     | Displays all current open positions with their PnL (absolute + %) |
| `normal`        | Switches bot to **normal** trading strategy (full-sized, longer SL/TP) |
| `conservative`  | Switches bot to **conservative** mode: smaller lots, tighter SL/TP |
| `/help`         | Shows this list of commands |

---

## 🧠 Trading Modes

### 🔄 Normal Mode
- Uses standard lot sizing from settings
- Dynamic SL/TP based on ATR + confidence

### ⚠️ Conservative Mode
- Reduces position size
- Tightens SL/TP
- Used to protect capital after hitting daily profit goals or on-demand via command

---

## 📊 SL/TP Calculation

- Base SL = `ATR × SL_MULTIPLIER`
- Base TP = `SL × TP_FACTOR + Confidence Boost`
- Enforced minimum % from `settings.py` (e.g. 0.2% SL minimum)

---

## 📆 Auto-disable Times
- Weekends (Saturday–Sunday)
- Custom holidays from `config/holidays.txt`

---

## 🧪 Requirements
- Python 3.9+
- `MetaTrader5`, `ta`, `numpy`, `pandas`, `tensorflow`, `requests`

---

Happy Trading 💸
