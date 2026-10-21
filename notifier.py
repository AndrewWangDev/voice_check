import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_telegram_alert(bot_token, chat_id, message, proxy=None):
    """
    Sends a message to the specified Telegram chat.
    Supports optional HTTP/SOCKS5 proxy and detailed error reporting.
    """
    if not bot_token or not chat_id:
        logging.error("Telegram Bot Token or Chat ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    try:
        response = requests.post(url, json=payload, timeout=10, proxies=proxies)
        if response.status_code != 200:
            error_desc = "Unknown error"
            try:
                error_desc = response.json().get("description", response.text)
            except Exception:
                error_desc = response.text
            logging.error(f"Failed to send Telegram notification (Status {response.status_code}): {error_desc}")
            return False

        logging.info(f"Notification sent: {message}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Telegram notification due to network error: {e}")
        return False

if __name__ == "__main__":
    # Test block
    print("This module is intended to be imported.")
