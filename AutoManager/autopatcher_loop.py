# autopatcher_loop.py

import time
from AutoManager import settings_manager as mgr_set
from AutoManager.integrator import integrate_modification
from telegram_notifier import send_telegram_message


def autopatcher_loop():
    send_telegram_message("🚀 AutoPatcher avviato. Controllo ciclico ogni {0} sec...".format(mgr_set.MONITOR_INTERVAL_SECONDS))

    while True:
        try:
            integrate_modification()
        except Exception as e:
            send_telegram_message(f"❌ Errore nel ciclo AutoPatcher: {e}")
        time.sleep(mgr_set.MONITOR_INTERVAL_SECONDS)


if __name__ == "__main__":
    autopatcher_loop()
