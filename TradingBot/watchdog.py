# watchdog.py

import os
import subprocess
import sys
import time
import requests
import settings
import MetaTrader5 as mt5
import psutil
from datetime import datetime

# === Configurazione ===
BOT_PROCESS_NAME = "bot.py"
CRASH_FLAG_PATH = "TRADING_BOT_CRASHED.flag"
LOG_DIR = "logs"
CHECK_INTERVAL = 60  # secondi

TELEGRAM_TOKEN = settings.TELEGRAM_TOKEN
CHAT_ID = settings.TELEGRAM_CHAT_ID
MT5_EQUITY_THRESHOLD = settings.EQUITY_ALERT_THRESHOLD
MAX_FAILURES = getattr(settings, "MAX_FAILURES", 3)

# === Risorse dinamiche ===
total_mem_mb = psutil.virtual_memory().total / (1024 * 1024)
RAM_ALERT_MB = total_mem_mb * 0.75
RAM_KILL_MB = total_mem_mb * 0.90
CPU_ALERT = 80
CPU_KILL = 95

failure_count = 0

def send_telegram(msg: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print(f"[Watchdog] Telegram fail: {e}")

def is_bot_running() -> bool:
    try:
        return any(BOT_PROCESS_NAME in p.info["cmdline"] for p in psutil.process_iter(["cmdline"]))
    except Exception as e:
        print(f"[Watchdog] is_bot_running() error: {e}")
        return False

def check_equity() -> float | None:
    try:
        if not mt5.initialize():
            return None
        eq = mt5.account_info().equity
        mt5.shutdown()
        return eq
    except Exception as e:
        print(f"[Watchdog] MT5 error: {e}")
        return None

def check_resources() -> bool:
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().used / (1024 * 1024)
    if cpu > CPU_KILL or mem > RAM_KILL_MB:
        send_telegram(f"🚨 Bot killed: CPU={cpu}%, RAM={mem:.0f}MB")
        kill_bot()
        return False
    if cpu > CPU_ALERT or mem > RAM_ALERT_MB:
        send_telegram(f"⚠️ CPU/RAM alta: CPU={cpu}%, RAM={mem:.0f}MB")
    return True

def kill_bot():
    global failure_count
    try:
        for p in psutil.process_iter(["cmdline"]):
            if BOT_PROCESS_NAME in " ".join(p.info.get("cmdline", [])):
                p.kill()
        failure_count = 0
        with open(CRASH_FLAG_PATH, "w") as f:
            f.write("bot_crashed")
    except Exception as e:
        print(f"[Watchdog] kill_bot() error: {e}")

def restart_bot():
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(LOG_DIR, f"restart_{ts}.log")
    with open(log_path, "w") as f:
        subprocess.Popen([sys.executable, BOT_PROCESS_NAME], stdout=f, stderr=subprocess.STDOUT)
    with open(CRASH_FLAG_PATH, "w") as f:
        f.write("bot_restarted")
    send_telegram(f"🔁 Bot riavviato. Log: {log_path}")

def main():
    global failure_count
    send_telegram("👁 Watchdog avviato")

    while True:
        alive = is_bot_running()
        eq = check_equity()
        res = check_resources()

        if not alive:
            failure_count += 1
            send_telegram(f"❌ Bot down ({failure_count}/{MAX_FAILURES})")
            if failure_count >= MAX_FAILURES:
                restart_bot()
        else:
            failure_count = 0

        if eq and eq < MT5_EQUITY_THRESHOLD:
            send_telegram(f"📉 Equity sotto soglia: {eq:.2f}")
            kill_bot()

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    if getattr(settings, "USE_LOCAL_WATCHDOG", True):
        main()
