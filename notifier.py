import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_telegram_alert(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        logging.error("Telegram Bot Token or Chat ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logging.info(f"Notification sent: {message}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Telegram notification: {e}")
        return False

if __name__ == "__main__":
    # Test block
    print("This module is intended to be imported.")
