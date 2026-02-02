import os
import sys
import queue
import json
import pyaudio
import logging
import zipfile
import requests
import threading
from vosk import Model, KaldiRecognizer
from notifier import send_telegram_alert

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
MODEL_NAME = "vosk-model-small-cn-0.22"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
AUDIO_RATE = 16000
CHUNK_SIZE = 4096

class VoiceAlertSystem:
    def __init__(self, bot_token, chat_id, keywords, on_log=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.keywords = keywords
        self.on_log = on_log  # Callback function for GUI logging
        self.running = False
        self.thread = None
        self.model = None

    def log(self, message):
        #Logs to console and GUI callback if available.
        logging.info(message)
        if self.on_log:
            self.on_log(message)

    def download_and_unpack_model(self):
        #Downloads the Vosk model checks if it exists.
        if os.path.exists(MODEL_NAME):
            self.log(f"Model '{MODEL_NAME}' found.")
            return MODEL_NAME
        
        self.log(f"Model '{MODEL_NAME}' not found. Downloading...")
        try:
            response = requests.get(MODEL_URL, stream=True)
            response.raise_for_status()
            
            zip_path = f"{MODEL_NAME}.zip"
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.log("Unpacking model")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(".")
            
            os.remove(zip_path)
            self.log("Model setup complete.")
            return MODEL_NAME
        except Exception as e:
            self.log(f"Error: Failed to download/unpack model: {e}")
            return None

    def load_model(self):
        if self.model:
            return True
        
        model_path = self.download_and_unpack_model()
        if not model_path:
            return False
            
        try:
            self.model = Model(model_path)
            return True
        except Exception as e:
            self.log(f"Error: Failed to load model: {e}")
            return False

    def start_detection(self):
        if self.running:
            self.log("Already running.")
            return

        if not self.load_model():
            return

        self.running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        self.log("Detection started.")

    def stop_detection(self):
        #Stops the detection loop.
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.log("Detection stopped.")

    def _detection_loop(self):
        q = queue.Queue()

        def callback(in_data, frame_count, time_info, status):
            if status:
                logging.warning(status, file=sys.stderr)
            q.put(bytes(in_data))
            return (None, pyaudio.paContinue)

        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=AUDIO_RATE,
                            input=True,
                            frames_per_buffer=CHUNK_SIZE,
                            stream_callback=callback)
            stream.start_stream()
            self.log("Listening...")
        except Exception as e:
            self.log(f"Error: Failed to open audio stream: {e}")
            self.running = False
            return

        rec = KaldiRecognizer(self.model, AUDIO_RATE)
        
        while self.running:
            try:
                # Non-blocking get with timeout to allow checking self.running
                data = q.get(timeout=1) 
            except queue.Empty:
                continue

            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").replace(" ", "")
                self._process_text(text)
            else:
                pass
                # partial = json.loads(rec.PartialResult())

        stream.stop_stream()
        stream.close()
        p.terminate()

    def _process_text(self, text):
        if not text:
            return
        
        for keyword in self.keywords:
            if keyword in text:
                msg = f"Keyword Detected: {keyword}"
                self.log(msg)
                # Telegram Token not set.
                if self.bot_token == "YOUR_BOT_TOKEN":
                   self.log("Warning: Telegram Token not set.")
                else:
                   send_telegram_alert(self.bot_token, self.chat_id, msg)

if __name__ == "__main__":
    # for testing
    print("Use gui.py to run")
