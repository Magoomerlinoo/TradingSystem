# Send Telegram message
def send_message(text):
    try:
        bot.send_message(settings.TELEGRAM_CHAT_ID, text)
    except Exception as e:
        print(f"Telegram error: {e}")