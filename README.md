# Voice Alert System

A real-time voice monitoring application that listens for specific keywords and sends instant alerts via Telegram. Designed for offline use with the Vosk speech recognition engine.

## 🚀 Features

- **Real-time Keyword Detection**: continuously listens to microphone input to detect user-defined keywords (supports live streaming partial result detection).
- **Offline Speech Recognition**: Uses the lightweight and accurate [Vosk](https://alphacephei.com/vosk/) model (automatically downloads and validates the small Chinese model `vosk-model-small-cn-0.22`).
- **Telegram Integration**: Sends instant notifications to your Telegram chat when a keyword is detected, with connection pooling and credential leakage prevention.
- **User-Friendly GUI**: Built with [Flet](https://flet.dev/), providing a clean, responsive interface, model advance downloader, and Chinese/English bilingual support.
- **Log Monitoring**: View real-time logs with high-performance incremental rendering directly in the app.

## 🛠️ Technology Stack

- **[Python](https://www.python.org/)**: Core programming language.
- **[Flet](https://flet.dev/)**: Framework for building the graphical user interface.
- **[Vosk](https://alphacephei.com/vosk/)**: Offline speech recognition toolkit.
- **[PyAudio](https://people.csail.mit.edu/hubert/pyaudio/)**: Library for audio input/output.
- **[Requests](https://requests.readthedocs.io/)**: HTTP library for sending Telegram API requests (with SOCKS5 proxy support).
- **[PyInstaller](https://pyinstaller.org/)**: Tool for packaging the application into a standalone executable.

## 📋 Prerequisites

- Python 3.8 or higher.
- A Telegram Bot Token and Chat ID (for receiving alerts).
- A working microphone.

## 📦 Installation

1. **Clone the repository** (if applicable) or download the source code.

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: On Windows, you might need to install Visual C++ Build Tools for PyAudio if the wheel installation fails.*

## ▶️ Usage

1. **Run the application**:
   ```bash
   python gui.py
   ```

2. **Configure the settings**:
   - **Telegram Bot Token**: Enter the token provided by @BotFather.
   - **Chat ID**: Enter your personal or group Chat ID (you can use bots like @userinfobot to find this).
   - **Keywords**: Enter the keywords you want to monitor, separated by commas (e.g., `帮助, 救命, 报警`). *Note: The default model is `vosk-model-small-cn-0.22` optimized for Chinese speech.*

3. **Start Monitoring**:
   - Click the **Start Detection** (开始监听) button.
   - The application will check or download the Vosk model and start listening.
   - The status will change to "Running" and live logs will appear in the log window.

4. **Stop Monitoring**:
   - Click the **Stop Detection** (停止监听) button to stop listening.

## 🔨 Building (Optional)

To create a standalone executable:

```bash
python build.py
```
The executable will be generated in the `release/VoiceAlert` folder.

## 📄 License

MIT
