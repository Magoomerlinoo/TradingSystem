# telegram_notifier.py
import requests
from AutoManager import settings_manager as mgr_set


def send_telegram_message(message: str) -> bool:
    """
    Invia una notifica Telegram usando le impostazioni in settings_manager.
    Restituisce True se la richiesta HTTP ha successo, False altrimenti.
    """
    url = f"https://api.telegram.org/bot{mgr_set.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": mgr_set.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, data=payload)
        if not resp.ok:
            print(f"[TelegramNotifier] Errore invio Telegram: {resp.status_code} {resp.text}")
        return resp.ok
    except Exception as e:
        print(f"[TelegramNotifier] Eccezione invio Telegram: {e}")
        return False