import os
import sys
import queue
import json
import time
import shutil
import zipfile
import threading
import logging
import requests

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    Model = None
    KaldiRecognizer = None

from notifier import send_telegram_alert

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
MODEL_NAME = "vosk-model-small-cn-0.22"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
AUDIO_RATE = 16000
CHUNK_SIZE = 4096

def get_base_dir():
    """Returns application base directory, prioritizing _MEIPASS for PyInstaller read-only bundled assets."""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_data_dir():
    """
    Returns writable directory for persistent models and configs.
    Ensures persistent storage is never directed into a temporary _MEIPASS folder.
    Falls back to user application data directory if installation path is read-only.
    """
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    test_file = os.path.join(base, ".write_test")
    try:
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return base
    except (OSError, PermissionError):
        pass

    if os.name == 'nt':
        user_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "VoiceAlert")
    else:
        user_dir = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "VoiceAlert")
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def is_valid_vosk_model(model_dir):
    """Verifies that the essential model files exist."""
    if not model_dir or not os.path.isdir(model_dir):
        return False
    required = [
        os.path.join(model_dir, "am", "final.mdl"),
        os.path.join(model_dir, "conf", "model.conf"),
    ]
    return all(os.path.exists(p) for p in required)

def check_model_ready():
    """
    Checks if the Vosk speech recognition model is downloaded and structurally valid.
    
    Returns:
        tuple[bool, str | None, str]: (is_ready, model_path, status_text)
    """
    candidates = [
        os.path.join(get_data_dir(), MODEL_NAME),
        os.path.join(get_base_dir(), MODEL_NAME),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), MODEL_NAME),
        os.path.abspath(MODEL_NAME),
    ]
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, MODEL_NAME))

    # Remove duplicates while preserving order
    unique_candidates = []
    for c in candidates:
        if c not in unique_candidates:
            unique_candidates.append(c)

    for path in unique_candidates:
        if is_valid_vosk_model(path):
            files = os.listdir(path)
            return True, path, f"Ready ({len(files)} files)"

    return False, None, "Not downloaded"

def safe_extract_zip(zip_file, target_dir):
    """Safely extracts a ZIP archive preventing directory traversal (Zip Slip)."""
    resolved_target = os.path.realpath(target_dir)
    os.makedirs(resolved_target, exist_ok=True)

    with zipfile.ZipFile(zip_file, "r") as zf:
        if sys.version_info >= (3, 12):
            zf.extractall(resolved_target, filter='data')
        else:
            for member in zf.namelist():
                member_path = os.path.realpath(os.path.join(resolved_target, member))
                if not (member_path == resolved_target or member_path.startswith(resolved_target + os.sep)):
                    raise ValueError(f"Path traversal detected in zip archive: {member}")
            zf.extractall(resolved_target)

def download_model(proxy=None, on_progress=None, on_log=None, is_cancelled=None):
    """
    Downloads and extracts the Vosk model archive safely using a temporary staging directory.
    
    Args:
        proxy (str): Optional HTTP/SOCKS proxy.
        on_progress (callable): callback(downloaded_bytes: int, total_bytes: int, percent: float)
        on_log (callable): callback(msg: str)
        is_cancelled (callable): callback() -> bool
        
    Returns:
        tuple[bool, str]: (success, model_path_or_error)
    """
    def _log(msg):
        logging.info(msg)
        if on_log:
            try:
                on_log(msg)
            except Exception:
                pass

    dest_dir = get_data_dir()
    zip_path = os.path.join(dest_dir, f"{MODEL_NAME}.zip")
    temp_extract_dir = os.path.join(dest_dir, f"{MODEL_NAME}_tmp")
    final_model_path = os.path.join(dest_dir, MODEL_NAME)
    proxies = {"http": proxy, "https": proxy} if proxy else None

    _log(f"Starting model download from {MODEL_URL}...")
    try:
        response = requests.get(MODEL_URL, stream=True, timeout=(10, 30), proxies=proxies)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        last_log_percent = -10

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=32768):
                if is_cancelled and is_cancelled():
                    _log("Model download cancelled.")
                    return False, "Cancelled"
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = (downloaded / total_size * 100.0) if total_size > 0 else 0.0
                    if on_progress:
                        try:
                            on_progress(downloaded, total_size, percent)
                        except Exception:
                            pass
                    if int(percent) - last_log_percent >= 10:
                        last_log_percent = int(percent)
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        _log(f"Downloading model: {mb_down:.1f}MB / {mb_total:.1f}MB ({percent:.1f}%)")

        _log("Download complete. Extracting model safely...")
        if on_progress:
            try:
                on_progress(total_size, total_size, 100.0)
            except Exception:
                pass

        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir, ignore_errors=True)

        safe_extract_zip(zip_path, temp_extract_dir)

        # Locate extracted model dir inside temp extract dir
        extracted_model_dir = os.path.join(temp_extract_dir, MODEL_NAME)
        source_dir = extracted_model_dir if os.path.exists(extracted_model_dir) else temp_extract_dir

        if not is_valid_vosk_model(source_dir):
            raise ValueError("Extracted model failed integrity verification (missing final.mdl or model.conf).")

        # Atomic replacement of target model directory
        if os.path.exists(final_model_path):
            shutil.rmtree(final_model_path, ignore_errors=True)
        shutil.move(source_dir, final_model_path)
        shutil.rmtree(temp_extract_dir, ignore_errors=True)

        _log(f"Model successfully verified and installed to: {final_model_path}")
        return True, final_model_path
    except Exception as e:
        err_msg = f"Failed to download or unpack model: {e}"
        _log(f"Error: {err_msg}")
        return False, err_msg
    finally:
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                pass
        if os.path.exists(temp_extract_dir):
            try:
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            except OSError:
                pass

class VoiceAlertSystem:
    def __init__(self, bot_token, chat_id, keywords, proxy=None, on_log=None, on_status_change=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Normalize keywords: strip internal and surrounding spaces, and lowercase
        # Ensures words like "help me" match normalized text "helpme"
        self.keywords = [k.replace(" ", "").lower() for k in keywords if k.strip()]
        self.proxy = proxy
        self.on_log = on_log  # Callback function for GUI logging
        self.on_status_change = on_status_change  # Callback for status change (bool: is_running, str: status_msg)
        self.running = False
        self.thread = None
        self.model = None
        
        # Cooldown management: keyword -> last alert timestamp
        self._last_alert_time = {}
        self._alert_cooldown = 5.0  # 5-second cooldown per keyword
        
        # Asynchronous notification queue & worker
        self._alert_queue = queue.Queue()
        self._alert_worker_thread = None

    def log(self, message):
        """Logs to console and GUI callback if available."""
        logging.info(message)
        if self.on_log:
            try:
                self.on_log(message)
            except Exception as e:
                logging.error(f"Error in on_log callback: {e}")

    def download_and_unpack_model(self):
        """Checks if model is ready; if not, downloads and unpacks it."""
        ready, model_path, _ = check_model_ready()
        if ready:
            self.log(f"Model found at: {model_path}")
            return model_path

        self.log(f"Model not found. Downloading from {MODEL_URL}...")
        success, res = download_model(
            proxy=self.proxy,
            on_log=self.log,
            is_cancelled=lambda: not self.running
        )
        if success:
            self.log("Model setup complete.")
            return res
        return None

    def load_model(self):
        if self.model:
            return True
        
        if Model is None:
            self.log("Error: 'vosk' module is not installed. Please run: pip install vosk")
            return False
        
        model_path = self.download_and_unpack_model()
        if not model_path:
            return False
            
        try:
            self.log("Loading speech recognition model...")
            self.model = Model(model_path)
            self.log("Model loaded successfully.")
            return True
        except Exception as e:
            self.log(f"Error: Failed to load model: {e}")
            return False

    def start_detection(self):
        """Starts model loading and detection loop in a dedicated background thread."""
        if self.running:
            self.log("Already running.")
            return

        self.running = True
        self.thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.thread.start()

    def _worker_thread(self):
        try:
            if self.on_status_change:
                self.on_status_change(True, "Loading model...")

            if not self.load_model():
                self.running = False
                if self.on_status_change:
                    self.on_status_change(False, "Failed to load model")
                return

            if not self.running:
                return

            if self.on_status_change:
                self.on_status_change(True, "Running")

            # Start asynchronous alert worker
            self._start_alert_worker()
            self._detection_loop()
        except Exception as e:
            self.log(f"Unexpected error in worker thread: {e}")
        finally:
            self.running = False
            if self.on_status_change:
                self.on_status_change(False, "Stopped")

    def stop_detection(self):
        """Stops the detection loop and waits for thread cleanup."""
        if not self.running:
            return
        
        self.running = False
        if self.thread and threading.current_thread() != self.thread:
            self.thread.join(timeout=3)
        self.log("Detection stopped.")

    def _start_alert_worker(self):
        """Launches a dedicated thread for non-blocking Telegram notifications."""
        def alert_loop():
            while self.running or not self._alert_queue.empty():
                try:
                    msg = self._alert_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if self.bot_token == "YOUR_BOT_TOKEN":
                    self.log("Warning: Telegram Token not configured.")
                else:
                    success = send_telegram_alert(self.bot_token, self.chat_id, msg, proxy=self.proxy)
                    if not success:
                        self.log(f"Failed to deliver alert: {msg}")
                self._alert_queue.task_done()

        self._alert_worker_thread = threading.Thread(target=alert_loop, daemon=True)
        self._alert_worker_thread.start()

    def _detection_loop(self):
        if pyaudio is None:
            self.log("Error: 'pyaudio' module is not installed. Please run: pip install pyaudio")
            self.running = False
            return

        audio_queue = queue.Queue()
        stream_status_flag = [0]

        # PyAudio callback runs in real-time audio thread: Keep it lightweight and non-blocking
        def callback(in_data, frame_count, time_info, status):
            if status:
                stream_status_flag[0] = status
            audio_queue.put(bytes(in_data))
            return (None, pyaudio.paContinue)

        p = None
        stream = None
        try:
            p = pyaudio.PyAudio()
            try:
                stream = p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=AUDIO_RATE,
                                input=True,
                                frames_per_buffer=CHUNK_SIZE,
                                stream_callback=callback)
            except Exception as e:
                self.log(f"Error opening audio stream at {AUDIO_RATE}Hz: {e}")
                self.log("Tip: Please check if your microphone is connected and authorized in Windows Privacy Settings.")
                return

            stream.start_stream()
            self.log("Listening for keywords...")

            rec = KaldiRecognizer(self.model, AUDIO_RATE)
            
            while self.running:
                if stream_status_flag[0] != 0:
                    status_code = stream_status_flag[0]
                    stream_status_flag[0] = 0
                    logging.warning(f"PyAudio stream status: {status_code}")

                try:
                    # Non-blocking get with timeout to allow checking self.running
                    data = audio_queue.get(timeout=0.5) 
                except queue.Empty:
                    continue

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").replace(" ", "").lower()
                    self._process_text(text)
                else:
                    # Process PartialResult for real-time immediate detection without sentence-end delay
                    partial_res = json.loads(rec.PartialResult())
                    partial_text = partial_res.get("partial", "").replace(" ", "").lower()
                    if partial_text:
                        # If a keyword is hit in the live stream, fire alert immediately and reset
                        if self._process_text(partial_text):
                            rec.Reset()

            # Process final residual audio buffer
            try:
                final_res = json.loads(rec.FinalResult())
                final_text = final_res.get("text", "").replace(" ", "").lower()
                self._process_text(final_text)
            except Exception:
                pass

        except Exception as e:
            self.log(f"Error in audio stream: {e}")
        finally:
            # Resource cleanup in finally block to prevent leak
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass
            self.log("Audio stream closed.")

    def _process_text(self, text):
        """
        Matches keywords in text. Returns True if a new alert was fired.
        """
        if not text:
            return False
        
        fired = False
        now = time.time()
        for keyword in self.keywords:
            if keyword in text:
                # Cooldown check to prevent alert spamming
                last_time = self._last_alert_time.get(keyword, 0)
                if now - last_time < self._alert_cooldown:
                    continue
                self._last_alert_time[keyword] = now
                
                msg = f"Keyword Detected: {keyword}"
                self.log(msg)
                # Enqueue to background alert worker (non-blocking)
                self._alert_queue.put(msg)
                fired = True

        return fired

if __name__ == "__main__":
    print("Use gui.py to run")
