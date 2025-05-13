
# 💹 AI-Powered Forex Trading Bot – Technical Spec

## 🧠 Core Features

- Multi-Timeframe AI Strategy: M5, M15, H1
- Hybrid Signal Fusion: LSTM + CNN + Sentiment + Classical
- Adaptive SL/TP & Sizing using ATR and market phase
- Dynamic model retraining & combo learning
- Symbol auto-onboarding with no manual prep

## 📊 Risk Management

- Daily loss limit shutdown
- Max consecutive trade failures
- Equity threshold alerts
- Phase-based flip cooldowns
- Trailing stop, partial TP, break-even logic

## 🤖 AI Models

- **LSTM**: Multi-class trend predictor (flat / up / down)
- **CNN**: Pattern scoring with continuous probability output
- **Sentiment**: Real-time news scanning using DistilBERT
- Auto-retraining from enriched CSV logs

## 📬 Telegram Interface

- `/risk` — update trade risk live
- `/mode conservative` — switch strategy style
- `/sentiment SYMBOL` — live NLP-based score
- `/performance` — PnL tracker (24h / 7d / 30d)
- `/shutdown` — trigger graceful bot stop

## ⚙️ Architecture

- Modular file structure: `models/`, `utils/`, `logic/`, `execution/`
- Auto-retraining + model hot reload
- JSON + CSV + Excel trade logs
- Live debug via CLI + Telegram
- Failsafe disconnect handlers + log alerts

## 🧪 Backtesting / Simulation Ready

- Data sourced via MT5 or Yahoo fallback
- Enriched datasets reusable for training
- Visual performance logs with candlestick overlay

## 🛡️ Final Hardening

- ✅ All logic paths reviewed
- ✅ Edge case protection
- ✅ Full input/output testing
- ✅ Production-ready for demo or live
