# run.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import subprocess
import time
import threading
from AutoManager.supervisor import try_fix_file
from AutoManager.autopatch_loop import autopatch_loop
from telegram_notifier import send_telegram_message

# All'avvio:
try_fix_file("TradingBot/bot.py")
try_fix_file("TradingBot/settings.py")

# Percorsi base
TRADING_BOT_PATH = r"C:\Users\Administrator\Desktop\TradingSystem\TradingBot"
AUTOMANAGER_PATH = os.path.dirname(__file__)
CRASH_FLAG = os.path.join(AUTOMANAGER_PATH, "TRADING_BOT_CRASHED.flag")


def launch_trading_bot():
    """Lancia il main.py del bot principale."""
    try:
        print("[Launcher] Avvio TradingBot...")
        return subprocess.Popen(["python", "main.py"], cwd=TRADING_BOT_PATH)
    except Exception as e:
        print(f"[Launcher] Errore avvio bot: {e}")
        return None


def launch_supervisor():
    """Lancia il supervisor manager in parallelo."""
    try:
        print("[Launcher] Avvio AutoManager...")
        return subprocess.Popen(["python", "supervisor.py"], cwd=AUTOMANAGER_PATH)
    except Exception as e:
        print(f"[Launcher] Errore avvio supervisor: {e}")
        return None


def monitor_crash_and_restart(bot_proc):
    """Monitora il flag di crash e riavvia dopo patch."""
    while True:
        if os.path.exists(CRASH_FLAG):
            print("[Launcher] ⚠️ Crash rilevato nel TradingBot.")
            send_telegram_message("⚠️ *Crash rilevato nel TradingBot.* Attesa fix...")

            while os.path.exists(CRASH_FLAG):
                time.sleep(10)

            print("[Launcher] ✅ Patch applicata, riavvio TradingBot.")
            send_telegram_message("♻️ *Patch applicata.* Riavvio del TradingBot...")

            if bot_proc.poll() is None:
                bot_proc.terminate()

            time.sleep(3)
            bot_proc = launch_trading_bot()
        time.sleep(5)


def main():
    if os.path.exists("RESTART_PENDING.flag"):
        send_telegram_message("⚠️ Riavvio richiesto: presente `RESTART_PENDING.flag`")

    bot_proc = launch_trading_bot()
    launch_supervisor()

    monitor_thread = threading.Thread(
        target=monitor_crash_and_restart,
        args=(bot_proc,),
        daemon=True
    )
    monitor_thread.start()

    autopatch_thread = threading.Thread(
        target=autopatch_loop,
        daemon=True
    )
    autopatch_thread.start()

    bot_proc.wait()
    print("[Launcher] 🔝 Bot terminato.")


if __name__ == "__main__":
    main()