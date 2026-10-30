import builtins
import sys

# PyInstaller frozen environment does not define exit/quit in builtins by default
if not hasattr(builtins, "exit"):
    builtins.exit = sys.exit
if not hasattr(builtins, "quit"):
    builtins.quit = sys.exit

import re
import os
import json
import threading
import time
import flet as ft
try:
    import flet_desktop
except ImportError:
    flet_desktop = None

def is_valid_flet_view_dir(path):
    """Checks whether the directory contains a platform-valid Flet client executable or bundle."""
    if not path or not os.path.isdir(path):
        return False
    if sys.platform == "win32":
        return os.path.isfile(os.path.join(path, "flet.exe"))
    elif sys.platform == "darwin":
        if os.path.isfile(os.path.join(path, "flet")):
            return True
        for name in os.listdir(path):
            if name.endswith(".app"):
                return True
        return False
    else:  # Linux / Unix
        return os.path.isfile(os.path.join(path, "flet"))

# Configure Flet Desktop client path for standalone bundled distribution
if getattr(sys, "frozen", False):
    exe_dir = os.path.dirname(sys.executable)
    for cand in [
        os.path.join(exe_dir, "_internal", "flet_view"),
        os.path.join(exe_dir, "flet_view"),
        os.path.join(getattr(sys, "_MEIPASS", ""), "flet_view"),
    ]:
        if is_valid_flet_view_dir(cand):
            os.environ["FLET_VIEW_PATH"] = os.path.abspath(cand)
            break

from main import VoiceAlertSystem, check_model_ready, download_model, MODEL_NAME, get_data_dir

# Cross-version compatibility aliases for modern Flet (0.25+ / 0.80+ / 1.0) and legacy Flet
Colors = getattr(ft, "Colors", getattr(ft, "colors", None))
Icons = getattr(ft, "Icons", getattr(ft, "icons", None))
ButtonControl = getattr(ft, "Button", getattr(ft, "ElevatedButton", None))

def make_border(color, width=1):
    """Safely creates a border across different Flet versions."""
    if hasattr(ft, "Border") and hasattr(ft.Border, "all"):
        return ft.Border.all(width, color)
    elif hasattr(ft, "border") and hasattr(ft.border, "all"):
        return ft.border.all(width, color)
    return None

def make_padding(h=0, v=0):
    """Safely creates symmetric padding across different Flet versions."""
    if hasattr(ft, "Padding") and hasattr(ft.Padding, "symmetric"):
        return ft.Padding.symmetric(horizontal=h, vertical=v)
    elif hasattr(ft, "padding") and hasattr(ft.padding, "symmetric"):
        return ft.padding.symmetric(horizontal=h, vertical=v)
    return h

def get_center_alignment():
    """Safely returns center alignment across different Flet versions."""
    if hasattr(ft, "Alignment"):
        return ft.Alignment(0, 0)
    elif hasattr(ft, "alignment") and hasattr(ft.alignment, "center"):
        return ft.alignment.center
    return None

def get_base_path():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_asset_path(filename):
    """Locates resource file in bundled dir or local script dir."""
    candidates = [
        os.path.join(get_base_path(), filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        filename
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, filename))
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None

def get_asset_bytes(filename):
    """Loads asset as raw bytes to ensure reliable embedding."""
    candidates = [
        os.path.join(get_base_path(), filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        filename
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    return f.read()
            except Exception:
                pass
    return None

def get_config_path():
    return os.path.join(get_data_dir(), "config.json")

def load_saved_config():
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_user_config(token, chat_id, proxy, keywords, lang):
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "bot_token": token,
                "chat_id": chat_id,
                "proxy": proxy,
                "keywords": keywords,
                "lang": lang
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def safe_copy_clipboard(page, text):
    """Safely sets clipboard text across different Flet versions."""
    try:
        if hasattr(page, "set_clipboard"):
            page.set_clipboard(text)
            return True
        elif hasattr(page, "clipboard") and hasattr(page.clipboard, "set"):
            page.clipboard.set(text)
            return True
    except Exception:
        pass
    return False

# Comprehensive Internationalization Dictionary
I18N = {
    "zh": {
        "title": "Voice Alert",
        "subtitle": "离线语音关键词实时监控预警系统",
        "lang_btn": "EN",
        "status_ready": "就绪",
        "status_initializing": "初始化中...",
        "status_running": "正在监听语音...",
        "status_stopped": "已停止",
        "sys_config": "系统配置",
        "bot_token_label": "Telegram Bot Token",
        "bot_token_hint": "粘贴来自 @BotFather 的 Token",
        "chat_id_label": "Telegram Chat ID",
        "chat_id_hint": "例如: 123456789 或 @my_channel",
        "proxy_label": "网络代理 (可选，用于 Telegram 直连)",
        "proxy_hint": "例如: http://127.0.0.1:7890 或 socks5://127.0.0.1:1080",
        "keywords_label": "监控关键词",
        "keywords_hint": "输入待监控中文词汇，支持中英文逗号、顿号或换行分隔（如：帮助，救命，开门）",
        "model_section_title": "语音识别离线模型 (Vosk Small CN)",
        "model_status_ready": "已就绪",
        "model_status_not_ready": "未就绪 (未下载)",
        "model_status_downloading": "下载中...",
        "model_status_unpacking": "正在解压...",
        "model_hint_ready": "本地模型就绪，已支持即时离线识别。",
        "model_hint_not_ready": "离线中文模型大小约 43MB。建议提前下载，避免首次监听等待。",
        "btn_download_model": "下载模型",
        "btn_redownload_model": "重新下载",
        "btn_downloading": "正在下载...",
        "model_download_success": "模型下载解压成功，已就绪！",
        "model_download_failed": "模型下载失败",
        "btn_start": "开始监听",
        "btn_stop": "停止监听",
        "terminal_title": "实时监控日志",
        "log_unit": "条记录",
        "copy_tooltip": "复制日志",
        "clear_tooltip": "清空日志",
        "copied": "已复制到剪贴板!",
        "err_token_chat": "Error: 请先完整填写 Telegram Bot Token 和 Chat ID。",
        "err_no_keywords": "Error: 请至少输入一个监控关键词。",
    },
    "en": {
        "title": "Voice Alert",
        "subtitle": "Real-time Voice Keyword Alert System (Vosk Offline CN)",
        "lang_btn": "中",
        "status_ready": "Ready",
        "status_initializing": "Initializing...",
        "status_running": "Listening...",
        "status_stopped": "Stopped",
        "sys_config": "Configuration",
        "bot_token_label": "Telegram Bot Token",
        "bot_token_hint": "Enter your Telegram Bot Token from @BotFather",
        "chat_id_label": "Telegram Chat ID",
        "chat_id_hint": "e.g. 123456789 or @my_channel",
        "proxy_label": "Network Proxy (Optional, for Telegram access)",
        "proxy_hint": "e.g. http://127.0.0.1:7890 or socks5://127.0.0.1:1080",
        "keywords_label": "Keywords to Monitor",
        "keywords_hint": "Offline model is Vosk Small CN. Enter Chinese keywords (e.g. 帮助, 救命, 报警)",
        "model_section_title": "Offline Speech Model (Vosk Small CN)",
        "model_status_ready": "Ready",
        "model_status_not_ready": "Not Ready (Not Downloaded)",
        "model_status_downloading": "Downloading...",
        "model_status_unpacking": "Extracting...",
        "model_hint_ready": "Local model ready. Instant offline voice recognition available.",
        "model_hint_not_ready": "Offline model is ~43MB. Download in advance for instant detection.",
        "btn_download_model": "Download Model",
        "btn_redownload_model": "Re-download",
        "btn_downloading": "Downloading...",
        "model_download_success": "Model downloaded and unpacked successfully!",
        "model_download_failed": "Model download failed",
        "btn_start": "Start Listening",
        "btn_stop": "Stop Listening",
        "terminal_title": "Live Monitor Logs",
        "log_unit": "entries",
        "copy_tooltip": "Copy logs",
        "clear_tooltip": "Clear logs",
        "copied": "Copied to clipboard!",
        "err_token_chat": "Error: Telegram Bot Token and Chat ID are required.",
        "err_no_keywords": "Error: At least one keyword is required.",
    }
}

def main(page: ft.Page):
    saved_cfg = load_saved_config()
    current_lang = saved_cfg.get("lang", "zh")
    if current_lang not in I18N:
        current_lang = "zh"

    def t(key):
        return I18N[current_lang].get(key, "")

    page.title = f"{t('title')} - {t('subtitle')}"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#111418"
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE

    # Cross-version desktop window configuration (Do NOT prevent close to guarantee instant exit)
    def configure_window():
        target_width = 720
        target_height = 880
        ico_path = get_asset_path("logo.ico")
        if hasattr(page, "window") and page.window is not None:
            try:
                page.window.width = target_width
                page.window.height = target_height
                page.window.min_width = 540
                page.window.min_height = 700
                page.window.prevent_close = False
                page.window.on_event = window_event
                if ico_path:
                    page.window.icon = ico_path
                return
            except Exception:
                pass
        try:
            page.window_width = target_width
            page.window_height = target_height
            page.window_prevent_close = False
            page.on_window_event = window_event
            if ico_path and hasattr(page, "window_icon"):
                page.window_icon = ico_path
        except Exception:
            pass

    app_is_alive = [True]

    def perform_clean_exit():
        """Cleanly stops detection and ensures the application process terminates."""
        app_is_alive[0] = False
        try:
            if system_holder["instance"]:
                system_holder["instance"].stop_detection()
        except Exception:
            pass
        os._exit(0)

    # Clean exit on disconnect (e.g. when user clicks X or window closes)
    page.on_disconnect = lambda _: perform_clean_exit()

    system_holder = {"instance": None}

    # Log entries buffer
    log_lines = []
    MAX_LOG_LINES = 200

    def get_log_color(text):
        lower = text.lower()
        if "error" in lower or "failed" in lower:
            return "#ff6b6b"
        elif "keyword detected" in lower or "报警" in lower:
            return "#ffd166"
        elif "listening" in lower or "started" in lower or "complete" in lower or "successfully" in lower:
            return "#06d6a0"
        elif "warning" in lower:
            return "#f4a261"
        return "#c9d1d9"

    def log_message(message):
        line = str(message)
        log_lines.append(line)
        if len(log_lines) > MAX_LOG_LINES:
            del log_lines[: len(log_lines) - MAX_LOG_LINES]

        # Incremental DOM update avoiding full O(N^2) recreation
        text_ctrl = ft.Text(
            line,
            size=12,
            font_family="Consolas, Cascadia Code, monospace",
            color=get_log_color(line),
            selectable=True,
        )
        log_list_view.controls.append(text_ctrl)
        if len(log_list_view.controls) > MAX_LOG_LINES:
            del log_list_view.controls[: len(log_list_view.controls) - MAX_LOG_LINES]

        log_counter_text.value = f"{len(log_list_view.controls)} {t('log_unit')}"
        try:
            page.update()
            log_list_view.scroll_to(offset=-1, duration=100)
        except Exception:
            pass

    def refresh_log_view():
        log_list_view.controls.clear()
        for line in log_lines:
            log_list_view.controls.append(
                ft.Text(
                    line,
                    size=12,
                    font_family="Consolas, Cascadia Code, monospace",
                    color=get_log_color(line),
                    selectable=True,
                )
            )
        log_counter_text.value = f"{len(log_lines)} {t('log_unit')}"
        try:
            page.update()
            log_list_view.scroll_to(offset=-1, duration=100)
        except Exception:
            pass

    def update_status_badge(running, msg):
        lower = msg.lower()
        display_text = msg
        if running:
            if "running" in lower or "监听" in lower:
                status_dot.bgcolor = "#06d6a0"
                status_badge.bgcolor = "#13382c"
                status_badge.border = make_border("#1d6f54", 1)
                status_text.color = "#06d6a0"
                display_text = t("status_running")
            else:
                status_dot.bgcolor = "#ffd166"
                status_badge.bgcolor = "#382f17"
                status_badge.border = make_border("#7a6125", 1)
                status_text.color = "#ffd166"
                display_text = t("status_initializing")
        else:
            status_dot.bgcolor = "#8b949e"
            status_badge.bgcolor = "#21262d"
            status_badge.border = make_border("#30363d", 1)
            status_text.color = "#8b949e"
            display_text = t("status_ready") if "ready" in lower or "就绪" in lower else t("status_stopped")

        status_text.value = display_text
        token_input.disabled = running
        chat_id_input.disabled = running
        proxy_input.disabled = running
        keywords_input.disabled = running
        start_btn.disabled = running
        stop_btn.disabled = not running
        try:
            page.update()
        except Exception:
            pass

    # Header section with Logo image
    logo_bytes = get_asset_bytes("logo.jpg")
    if logo_bytes:
        brand_logo = ft.Image(
            src=logo_bytes,
            width=46,
            height=46,
            border_radius=12,
        )
    else:
        icon_mic = getattr(Icons, "GRAPHIC_EQ_ROUNDED", None) or getattr(Icons, "MIC", None)
        brand_logo = ft.Container(
            content=ft.Icon(icon_mic, size=28, color="#38ef7d"),
            bgcolor="#16382b",
            border_radius=12,
            padding=10,
            border=make_border("#246146", 1),
        )

    title_text = ft.Text(t("title"), size=20, weight=ft.FontWeight.BOLD, color="#ffffff")
    subtitle_text = ft.Text(t("subtitle"), size=12, color="#8b949e")

    # Status indicator Badge
    status_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor="#8b949e")
    status_text = ft.Text(t("status_ready"), size=12, weight=ft.FontWeight.W_500, color="#8b949e")
    status_badge = ft.Container(
        content=ft.Row([status_dot, status_text], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        padding=make_padding(h=12, v=6),
        border_radius=20,
        bgcolor="#21262d",
        border=make_border("#30363d", 1),
    )

    # Language Toggle Button
    lang_btn_text = ft.Text(t("lang_btn"), size=12, weight=ft.FontWeight.BOLD, color="#58a6ff")
    
    def toggle_language(e):
        nonlocal current_lang
        current_lang = "en" if current_lang == "zh" else "zh"
        
        # Persist language choice
        save_user_config(
            (token_input.value or "").strip(),
            (chat_id_input.value or "").strip(),
            (proxy_input.value or "").strip(),
            (keywords_input.value or "").strip(),
            current_lang
        )
        
        # Update UI texts
        page.title = f"{t('title')} - {t('subtitle')}"
        title_text.value = t("title")
        subtitle_text.value = t("subtitle")
        lang_btn_text.value = t("lang_btn")
        
        # Status text
        is_running = system_holder["instance"] and system_holder["instance"].running
        update_status_badge(bool(is_running), t("status_running") if is_running else t("status_ready"))
        
        # Form labels & hints
        config_title_text.value = t("sys_config")
        token_input.label = t("bot_token_label")
        token_input.hint_text = t("bot_token_hint")
        chat_id_input.label = t("chat_id_label")
        chat_id_input.hint_text = t("chat_id_hint")
        proxy_input.label = t("proxy_label")
        proxy_input.hint_text = t("proxy_hint")
        keywords_input.label = t("keywords_label")
        keywords_input.hint_text = t("keywords_hint")
        
        # Action buttons
        start_btn_text.value = t("btn_start")
        stop_btn_text.value = t("btn_stop")
        
        # Terminal headers
        terminal_title_text.value = t("terminal_title")
        copy_icon_btn.tooltip = t("copy_tooltip")
        clear_icon_btn.tooltip = t("clear_tooltip")
        log_counter_text.value = f"{len(log_lines)} {t('log_unit')}"
        
        # Model card
        try:
            model_title_text.value = t("model_section_title")
            update_model_ui()
        except Exception:
            pass

        page.update()

    lang_switch_container = ft.Container(
        content=ft.Row(
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Icon(getattr(Icons, "TRANSLATE_ROUNDED", None) or getattr(Icons, "LANGUAGE", None), size=14, color="#58a6ff"),
                lang_btn_text
            ]
        ),
        padding=make_padding(h=10, v=6),
        border_radius=20,
        bgcolor="#182333",
        border=make_border("#26456f", 1),
        on_click=toggle_language,
        tooltip="切换语言 / Switch Language"
    )

    header_section = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Row(
                spacing=12,
                controls=[
                    brand_logo,
                    ft.Column(
                        spacing=2,
                        controls=[title_text, subtitle_text],
                    ),
                ],
            ),
            ft.Row(
                spacing=8,
                controls=[status_badge, lang_switch_container]
            ),
        ],
    )

    # Form Fields
    token_input = ft.TextField(
        label=t("bot_token_label"),
        value=saved_cfg.get("bot_token", ""),
        password=True,
        can_reveal_password=True,
        hint_text=t("bot_token_hint"),
        border_radius=8,
        border_color="#30363d",
        focused_border_color="#11998e",
        prefix_icon=getattr(Icons, "VPN_KEY_ROUNDED", None) or getattr(Icons, "KEY", None),
        text_size=13,
    )

    chat_id_input = ft.TextField(
        label=t("chat_id_label"),
        value=saved_cfg.get("chat_id", ""),
        hint_text=t("chat_id_hint"),
        border_radius=8,
        border_color="#30363d",
        focused_border_color="#11998e",
        prefix_icon=getattr(Icons, "SEND_ROUNDED", None) or getattr(Icons, "SEND", None),
        text_size=13,
    )

    proxy_input = ft.TextField(
        label=t("proxy_label"),
        value=saved_cfg.get("proxy", ""),
        hint_text=t("proxy_hint"),
        border_radius=8,
        border_color="#30363d",
        focused_border_color="#11998e",
        prefix_icon=getattr(Icons, "SHIELD_OUTLINED", None) or getattr(Icons, "SHIELD", None),
        text_size=13,
    )

    keywords_input = ft.TextField(
        label=t("keywords_label"),
        value=saved_cfg.get("keywords", "立正, 张三"),
        hint_text=t("keywords_hint"),
        multiline=True,
        min_lines=2,
        max_lines=3,
        border_radius=8,
        border_color="#30363d",
        focused_border_color="#11998e",
        prefix_icon=getattr(Icons, "TAG_ROUNDED", None) or getattr(Icons, "TAG", None),
        text_size=13,
    )

    config_title_text = ft.Text(t("sys_config"), size=14, weight=ft.FontWeight.W_600, color="#e6edf3")

    # Configuration Card
    config_card = ft.Container(
        padding=18,
        border_radius=12,
        bgcolor="#181c23",
        border=make_border("#282f3c", 1),
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(getattr(Icons, "TUNE_ROUNDED", None) or getattr(Icons, "SETTINGS", None), size=18, color="#58a6ff"),
                        config_title_text,
                    ],
                ),
                token_input,
                chat_id_input,
                proxy_input,
                keywords_input,
            ],
        ),
    )

    # Model Status and Download Section
    model_icon = getattr(Icons, "MEMORY_ROUNDED", None) or getattr(Icons, "SUBTITLES_ROUNDED", None) or getattr(Icons, "SETTINGS_VOICE", None)
    model_title_text = ft.Text(t("model_section_title"), size=14, weight=ft.FontWeight.W_600, color="#e6edf3")

    model_status_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor="#f4a261")
    model_status_text = ft.Text(t("model_status_not_ready"), size=12, weight=ft.FontWeight.W_500, color="#f4a261")
    model_badge = ft.Container(
        content=ft.Row([model_status_dot, model_status_text], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        padding=make_padding(h=10, v=4),
        border_radius=16,
        bgcolor="#382f17",
        border=make_border("#7a6125", 1),
    )

    model_hint_text = ft.Text(
        t("model_hint_not_ready"),
        size=12,
        color="#8b949e",
        no_wrap=False,
    )
    model_hint_container = ft.Container(
        width=440,
        content=model_hint_text,
    )

    model_progress_bar = ft.ProgressBar(
        value=0.0,
        bgcolor="#21262d",
        color="#11998e",
        height=5,
        border_radius=3,
        visible=False,
    )
    model_progress_text = ft.Text("", size=11, color="#8b949e", visible=False)

    download_icon = getattr(Icons, "DOWNLOAD_ROUNDED", None) or getattr(Icons, "DOWNLOAD", None)
    btn_download_text = ft.Text(t("btn_download_model"), size=12, weight=ft.FontWeight.W_600, color="#ffffff")

    def on_model_download_click(e):
        start_model_download()

    model_download_btn = ButtonControl(
        content=ft.Row([ft.Icon(download_icon, size=16, color="#ffffff"), btn_download_text], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        width=130,
        height=36,
        style=ft.ButtonStyle(
            color="#ffffff",
            bgcolor="#1f6feb",
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=on_model_download_click,
    )

    is_downloading_model = False

    def update_model_ui(override_status=None, progress_val=None, progress_str=None):
        nonlocal is_downloading_model
        if override_status == "downloading":
            is_downloading_model = True
            model_status_dot.bgcolor = "#58a6ff"
            model_badge.bgcolor = "#16273d"
            model_badge.border = make_border("#1f6feb", 1)
            model_status_text.color = "#58a6ff"
            model_status_text.value = t("model_status_downloading")
            btn_download_text.value = t("btn_downloading")
            model_download_btn.disabled = True
            model_progress_bar.visible = True
            model_progress_text.visible = True
            if progress_val is not None:
                model_progress_bar.value = progress_val
            if progress_str:
                model_progress_text.value = progress_str
        elif override_status == "unpacking":
            model_status_dot.bgcolor = "#a371f7"
            model_badge.bgcolor = "#2e1e47"
            model_badge.border = make_border("#a371f7", 1)
            model_status_text.color = "#a371f7"
            model_status_text.value = t("model_status_unpacking")
            btn_download_text.value = t("btn_downloading")
            model_download_btn.disabled = True
            model_progress_bar.visible = True
            model_progress_bar.value = 1.0
            model_progress_text.value = progress_str or t("model_status_unpacking")
        else:
            is_downloading_model = False
            ready, path, _ = check_model_ready()
            model_progress_bar.visible = False
            model_progress_text.visible = False
            model_download_btn.disabled = False
            if ready:
                model_status_dot.bgcolor = "#06d6a0"
                model_badge.bgcolor = "#13382c"
                model_badge.border = make_border("#1d6f54", 1)
                model_status_text.color = "#06d6a0"
                model_status_text.value = t("model_status_ready")
                model_hint_text.value = t("model_hint_ready")
                btn_download_text.value = t("btn_redownload_model")
                model_download_btn.style = ft.ButtonStyle(
                    color="#c9d1d9",
                    bgcolor="#21262d",
                    shape=ft.RoundedRectangleBorder(radius=8),
                )
            else:
                model_status_dot.bgcolor = "#f4a261"
                model_badge.bgcolor = "#382f17"
                model_badge.border = make_border("#7a6125", 1)
                model_status_text.color = "#f4a261"
                model_status_text.value = t("model_status_not_ready")
                model_hint_text.value = t("model_hint_not_ready")
                btn_download_text.value = t("btn_download_model")
                model_download_btn.style = ft.ButtonStyle(
                    color="#ffffff",
                    bgcolor="#1f6feb",
                    shape=ft.RoundedRectangleBorder(radius=8),
                )
        try:
            page.update()
        except Exception:
            pass

    def start_model_download():
        if is_downloading_model:
            return

        proxy_val = (proxy_input.value or "").strip() or None
        log_message(t("model_status_downloading") + (f" (Proxy: {proxy_val})" if proxy_val else ""))
        update_model_ui("downloading", 0.0, "0%")

        def bg_worker():
            last_ui_update = 0

            def on_progress(down, total, percent):
                nonlocal last_ui_update
                now = time.time()
                if now - last_ui_update > 0.15 or percent >= 100.0:
                    last_ui_update = now
                    down_mb = down / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    p_str = f"{down_mb:.1f} MB / {total_mb:.1f} MB ({percent:.0f}%)"
                    if percent >= 100.0:
                        update_model_ui("unpacking", 1.0, t("model_status_unpacking"))
                    else:
                        update_model_ui("downloading", percent / 100.0, p_str)

            success, res = download_model(
                proxy=proxy_val,
                on_progress=on_progress,
                on_log=log_message,
                is_cancelled=lambda: not app_is_alive[0]
            )

            if success:
                log_message(t("model_download_success"))
            else:
                log_message(f"{t('model_download_failed')}: {res}")

            update_model_ui()

        threading.Thread(target=bg_worker, daemon=True).start()

    model_card = ft.Container(
        padding=16,
        border_radius=12,
        bgcolor="#181c23",
        border=make_border("#282f3c", 1),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(model_icon, size=18, color="#a371f7"),
                                model_title_text,
                            ],
                        ),
                        model_badge,
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        model_hint_container,
                        model_download_btn,
                    ],
                ),
                model_progress_bar,
                model_progress_text,
            ],
        ),
    )

    # Button Event Handlers
    def start_click(e):
        token_val = (token_input.value or "").strip()
        chat_val = (chat_id_input.value or "").strip()
        proxy_val = (proxy_input.value or "").strip() or None
        keywords_val = (keywords_input.value or "").strip()

        if not token_val or not chat_val:
            log_message(t("err_token_chat"))
            return

        raw_keywords = re.split(r"[,，、\n]+", keywords_val)
        keywords = [k.strip() for k in raw_keywords if k.strip()]

        if not keywords:
            log_message(t("err_no_keywords"))
            return

        # Auto save user configuration
        save_user_config(token_val, chat_val, proxy_val or "", keywords_val, current_lang)

        update_status_badge(True, t("status_initializing"))

        def on_system_status(running, msg):
            update_status_badge(running, msg)
            if not running or "running" in msg.lower():
                update_model_ui()

        system_holder["instance"] = VoiceAlertSystem(
            bot_token=token_val,
            chat_id=chat_val,
            keywords=keywords,
            proxy=proxy_val,
            on_log=log_message,
            on_status_change=on_system_status,
        )

        system_holder["instance"].start_detection()

    def stop_click(e):
        stop_btn.disabled = True
        try:
            page.update()
        except Exception:
            pass

        def bg_stop():
            try:
                if system_holder["instance"]:
                    system_holder["instance"].stop_detection()
            except Exception:
                pass
            update_status_badge(False, t("status_stopped"))

        threading.Thread(target=bg_stop, daemon=True).start()

    # Main Action Buttons (Explicit dimensions to prevent Flutter unbounded flex exception)
    play_icon = getattr(Icons, "PLAY_ARROW_ROUNDED", None) or getattr(Icons, "PLAY_ARROW", None)
    stop_icon = getattr(Icons, "STOP_ROUNDED", None) or getattr(Icons, "STOP", None)

    start_btn_text = ft.Text(t("btn_start"), color="#ffffff", size=14, weight=ft.FontWeight.W_600)
    stop_btn_text = ft.Text(t("btn_stop"), color="#ffffff", size=14, weight=ft.FontWeight.W_600)

    start_btn = ButtonControl(
        content=ft.Row([ft.Icon(play_icon, color="#ffffff", size=18), start_btn_text], alignment=ft.MainAxisAlignment.CENTER),
        on_click=start_click,
        width=190,
        height=44,
        style=ft.ButtonStyle(
            color="#ffffff",
            bgcolor="#11998e",
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )

    stop_btn = ButtonControl(
        content=ft.Row([ft.Icon(stop_icon, color="#ffffff", size=18), stop_btn_text], alignment=ft.MainAxisAlignment.CENTER),
        on_click=stop_click,
        disabled=True,
        width=190,
        height=44,
        style=ft.ButtonStyle(
            color="#ffffff",
            bgcolor="#da3633",
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )

    actions_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=24,
        controls=[start_btn, stop_btn],
    )

    # Terminal Log Component
    log_counter_text = ft.Text(f"0 {t('log_unit')}", size=11, color="#8b949e")

    def clear_logs(e):
        log_lines.clear()
        log_list_view.controls.clear()
        log_counter_text.value = f"0 {t('log_unit')}"
        try:
            page.update()
        except Exception:
            pass

    def copy_logs(e):
        all_text = "\n".join(log_lines)
        safe_copy_clipboard(page, all_text)
        log_counter_text.value = t("copied")
        page.update()
        def restore():
            time.sleep(2)
            log_counter_text.value = f"{len(log_lines)} {t('log_unit')}"
            try:
                page.update()
            except Exception:
                pass
        threading.Thread(target=restore, daemon=True).start()

    copy_icon = getattr(Icons, "CONTENT_COPY_ROUNDED", None) or getattr(Icons, "COPY", None)
    clear_icon = getattr(Icons, "DELETE_SWEEP_OUTLINED", None) or getattr(Icons, "CLEAR", None)

    copy_icon_btn = ft.IconButton(icon=copy_icon, icon_size=16, icon_color="#8b949e", tooltip=t("copy_tooltip"), on_click=copy_logs)
    clear_icon_btn = ft.IconButton(icon=clear_icon, icon_size=16, icon_color="#8b949e", tooltip=t("clear_tooltip"), on_click=clear_logs)

    log_list_view = ft.ListView(
        spacing=4,
        auto_scroll=True,
        height=220,
    )

    terminal_title_text = ft.Text(t("terminal_title"), size=13, weight=ft.FontWeight.W_600, color="#e6edf3")

    terminal_header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(getattr(Icons, "TERMINAL_ROUNDED", None) or getattr(Icons, "TERMINAL", None), size=16, color="#58a6ff"),
                    terminal_title_text,
                    log_counter_text,
                ],
            ),
            ft.Row(
                spacing=4,
                controls=[
                    copy_icon_btn,
                    clear_icon_btn,
                ],
            ),
        ],
    )

    terminal_card = ft.Container(
        padding=16,
        border_radius=12,
        bgcolor="#0d1117",
        border=make_border("#21262d", 1),
        content=ft.Column(
            spacing=10,
            controls=[
                terminal_header,
                ft.Divider(height=1, color="#21262d"),
                log_list_view,
            ],
        ),
    )

    # Centered Master Wrapper (max-width prevents edge stretching on wide screens)
    layout_wrapper = ft.Container(
        width=640,
        alignment=get_center_alignment(),
        content=ft.Column(
            spacing=16,
            controls=[
                header_section,
                model_card,
                config_card,
                actions_row,
                terminal_card,
            ],
        ),
    )

    page.add(layout_wrapper)

    # Initial query of model readiness status on disk
    update_model_ui()

    # Clean exit on window close event
    def window_event(e):
        event_str = str(getattr(e, "data", "") or getattr(e, "type", "")).lower()
        if "close" in event_str:
            perform_clean_exit()

    configure_window()

def launch_app():
    if hasattr(ft, "run"):
        ft.run(main)
    elif hasattr(ft, "app"):
        ft.app(target=main)

if __name__ == "__main__":
    launch_app()
