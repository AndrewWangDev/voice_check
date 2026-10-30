import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global reusable session
_session = None

def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries, pool_connections=5, pool_maxsize=10)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session

def sanitize_telegram_error(text: str) -> str:
    """Masks bot token in error messages and URLs to prevent credential leakage."""
    if not text:
        return ""
    return re.sub(r'bot[0-9]+:[a-zA-Z0-9_-]+', 'bot***REDACTED***', str(text))

def send_telegram_alert(bot_token, chat_id, message, proxy=None):
    """
    Sends a message to the specified Telegram chat.
    Supports optional HTTP/SOCKS5 proxy, connection pooling, and token masking.
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
    session = get_session()
    
    try:
        response = session.post(url, json=payload, timeout=10, proxies=proxies)
        if response.status_code != 200:
            error_desc = "Unknown error"
            try:
                error_desc = response.json().get("description", response.text)
            except Exception:
                error_desc = response.text
            clean_desc = sanitize_telegram_error(error_desc)
            logging.error(f"Failed to send Telegram notification (Status {response.status_code}): {clean_desc}")
            return False

        logging.info(f"Notification sent: {message}")
        return True
    except requests.exceptions.RequestException as e:
        safe_msg = sanitize_telegram_error(str(e))
        logging.error(f"Failed to send Telegram notification due to network error: {safe_msg}")
        return False

if __name__ == "__main__":
    # Test block
    print("This module is intended to be imported.")
