# 🧠 AutoManager - README

## 📌 Scopo del Progetto
AutoManager è un sistema di auto-debugging e ottimizzazione continua per bot di trading basati su MetaTrader 5. Lavora in parallelo al bot principale (**TradingBot**) per:

- Monitorare le performance
- Correggere errori via GPT-4 (function-calling)
- Ottimizzare dinamicamente i parametri
- Applicare modifiche via patch JSON
- Loggare tutto con Telegram + GitHub

---

## 🧩 Architettura Modulare

```
📦 AutoManager
├── supervisor.py         ➞ loop principale
├── agent.py              ➞ invio richieste GPT + validazione
├── integrator.py         ➞ applica patch al codice o parametri
├── openai_manager.py     ➞ API OpenAI + SYSTEM_MSG
├── telegram_notifier.py  ➞ notifiche Telegram + report
├── github_uploader.py    ➞ push Git auto-commit
├── lock_manager.py       ➞ blocco modifiche ripetute
├── post_validation.py    ➞ controllo delta performance
├── state_writer.py       ➞ simulazione/metrica performance
├── test_full_cycle.py    ➞ test end-to-end GPT + patch
├── settings_manager.py   ➞ tutte le impostazioni del manager
```

---

## 🚀 Flusso Operativo

1. **Avvio `supervisor.py`** ogni `MONITOR_INTERVAL_SECONDS`
2. Verifica `state.json` → confronta con soglie minime
3. Se sotto target:
   - Applica patch JSON presenti (file → code_patch / param_update)
   - Invoca GPT (se `CALL_GPT_FOR_SUGGESTIONS = True`)
   - Salva il JSON e lo integra subito
4. Registra patch in `integration_logs/`
5. Se `ENABLE_AUTO_GIT_PUSH = True` → Git commit + push
6. Invia stato e notifiche via Telegram
7. Se patch peggiora le performance → rollback automatico

---

## 🔐 Sicurezza e Stabilità
- Patch controllate da `json_schema.py`
- Sistema di lock: evita patch ripetitive a ciclo breve
- Post-validation su profitto, precisione, drawdown
- Rollback automatico se il delta è negativo

---

## 🤖 Come usare AutoManager

### 1. Configura `settings_manager.py`
- `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `DAILY_PROFIT_TARGET`, ecc.

### 2. Avvia il bot principale (TradingBot)
- `python main.py`

### 3. Avvia AutoManager
- `python supervisor.py`

### 4. Testa un ciclo
- `python test_full_cycle.py`

---

## 🧪 Comandi da Telegram
| Comando       | Effetto                                  |
|---------------|--------------------------------------------|
| `/report`     | Stato attuale e ultima patch               |
| `/status`     | Performance, drawdown, precisione live     |
| `/forcepatch` | Invia manualmente una richiesta a GPT      |

---

## 📝 File e Directory Speciali
| Path                           | Scopo                            |
|--------------------------------|----------------------------------|
| `modification_logs/json/`      | Patch JSON ancora da integrare   |
| `modification_logs/processed/` | Patch già applicate              |
| `integration_logs/`            | Log dettagliato di ogni modifica |
| `integration_errors.log`       | Errori di integrazione           |
| `state.json`                   | Stato performance aggiornato     |

---

## 📎 Link Utili
- GPT-4 API: https://platform.openai.com
- Telegram Bot Creator: https://t.me/BotFather
- MetaTrader5 Python API: https://www.metaquotes.net/en/metatrader5/api/python

---

## © Credits
Progetto sviluppato da [TUO NOME] con integrazione GPT-4, MT5 e strumenti Python ad alta resilienza.
