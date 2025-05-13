# main.py

import subprocess
import time
import os
import psutil
from utils.runtime_optimizer import get_top_symbols, save_active_symbols
from settings import SYMBOLS

# Calcola dinamicamente il limite di simboli basato su memoria disponibile
def calculate_symbol_limit(estimate_per_symbol_mb=1024):
    proc = psutil.Process()
    total_mb = psutil.virtual_memory().total / (1024 * 1024)
    used_mb = proc.memory_info().rss / (1024 * 1024)
    # Teniamo libero il 20% della RAM e consideriamo un ulteriore margine del 20%
    headroom_mb = total_mb * 0.8 - used_mb
    limit = max(1, int(headroom_mb / estimate_per_symbol_mb * 0.8))
    print(f"[MAIN] Calculated symbol limit: {limit}")
    return limit

# Percorso assoluto di Python installato
PYTHON_PATH = r"C:\Program Files\Python310\python.exe"

def start_service(script_name, label):
    if not os.path.isfile(script_name):
        print(f"[MAIN] ⚠️ Script '{script_name}' non trovato.")
        return
    try:
        subprocess.Popen([PYTHON_PATH, script_name])
        print(f"[MAIN] ✅ {label} started.")
    except Exception as e:
        print(f"[MAIN] ❌ Failed to start {label}: {e}")

def main():
    print("🚀 Launching Trading Bot System...")

    # Calcolo dinamico del numero di simboli
    limit = calculate_symbol_limit()
    top_symbols = get_top_symbols(limit=limit)
    save_active_symbols(top_symbols)
    print(f"[MAIN] Active symbols ({len(top_symbols)}): {top_symbols}")

    # Avvia servizi in background
    start_service("telegram/telegram_bot.py", "Telegram Bot")
    start_service("watchdog.py", "Watchdog")
    time.sleep(2)  # Attendi inizializzazione

    # Avvia il trading bot principale
    try:
        subprocess.run([PYTHON_PATH, "bot.py"])
    except Exception as e:
        print(f"[MAIN] ❌ bot.py crashed: {e}")
        with open("TRADING_BOT_CRASHED.flag", "w") as f:
            f.write("crashed")    

if __name__ == "__main__":
    main()
