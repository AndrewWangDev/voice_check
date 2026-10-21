import re
import os
import json
import threading
import time
import flet as ft
from main import VoiceAlertSystem

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

def get_config_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "config.json")

def load_saved_config():
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_user_config(token, chat_id, proxy, keywords):
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "bot_token": token,
                "chat_id": chat_id,
                "proxy": proxy,
                "keywords": keywords
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

def main(page: ft.Page):
    page.title = "Voice Alert - 语音实时监控报警系统"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#111418"
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE

    # Cross-version desktop window configuration helper
    def configure_window():
        target_width = 720
        target_height = 880
        if hasattr(page, "window") and page.window is not None:
            try:
                page.window.width = target_width
                page.window.height = target_height
                page.window.min_width = 540
                page.window.min_height = 700
                page.window.prevent_close = True
                page.window.on_event = window_event
                return
            except Exception:
                pass
        try:
            page.window_width = target_width
            page.window_height = target_height
            page.window_prevent_close = True
            page.on_window_event = window_event
        except Exception:
            pass

    def close_window():
        if hasattr(page, "window") and page.window is not None:
            if hasattr(page.window, "destroy"):
                try:
                    page.window.destroy()
                    return
                except Exception:
                    pass
            elif hasattr(page.window, "close"):
                try:
                    page.window.close()
                    return
                except Exception:
                    pass
        if hasattr(page, "window_destroy"):
            try:
                page.window_destroy()
            except Exception:
                pass

    system_holder = {"instance": None}
    saved_cfg = load_saved_config()

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
        log_counter_text.value = f"{len(log_lines)} 条记录"
        try:
            page.update()
            log_list_view.scroll_to(offset=-1, duration=150)
        except Exception:
            pass

    def log_message(message):
        log_lines.append(str(message))
        if len(log_lines) > MAX_LOG_LINES:
            del log_lines[: len(log_lines) - MAX_LOG_LINES]
        refresh_log_view()

    def update_status_badge(running, msg):
        lower = msg.lower()
        if running:
            if "running" in lower or "监听" in lower:
                status_dot.bgcolor = "#06d6a0"
                status_badge.bgcolor = "#13382c"
                status_badge.border = make_border("#1d6f54", 1)
                status_text.color = "#06d6a0"
            else:
                status_dot.bgcolor = "#ffd166"
                status_badge.bgcolor = "#382f17"
                status_badge.border = make_border("#7a6125", 1)
                status_text.color = "#ffd166"
        else:
            status_dot.bgcolor = "#8b949e"
            status_badge.bgcolor = "#21262d"
            status_badge.border = make_border("#30363d", 1)
            status_text.color = "#8b949e"

        status_text.value = msg
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

    # Header components
    icon_mic = getattr(Icons, "GRAPHIC_EQ_ROUNDED", None) or getattr(Icons, "MIC", None)
    header_section = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Row(
                spacing=12,
                controls=[
                    ft.Container(
                        content=ft.Icon(icon_mic, size=28, color="#38ef7d"),
                        bgcolor="#16382b",
                        border_radius=12,
                        padding=10,
                        border=make_border("#246146", 1),
                    ),
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text("Voice Alert", size=20, weight=ft.FontWeight.BOLD, color="#ffffff"),
                            ft.Text("离线语音关键词实时监控预警系统", size=12, color="#8b949e"),
                        ],
                    ),
                ],
            ),
        ],
    )

    # Status indicator Badge
    status_dot = ft.Container(width=8, height=8, border_radius=4, bgcolor="#8b949e")
    status_text = ft.Text("就绪", size=12, weight=ft.FontWeight.W_500, color="#8b949e")
    status_badge = ft.Container(
        content=ft.Row([status_dot, status_text], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        padding=make_padding(h=12, v=6),
        border_radius=20,
        bgcolor="#21262d",
        border=make_border("#30363d", 1),
    )
    header_section.controls.append(status_badge)

    # Form Fields
    token_input = ft.TextField(
        label="Telegram Bot Token",
        value=saved_cfg.get("bot_token", ""),
        password=True,
        can_reveal_password=True,
        hint_text="粘贴来自 @BotFather 的 Token",
        border_radius=8,
        border_color="#30363d",
        focused_border_color="#11998e",
        prefix_icon=getattr(Icons, "VPN_KEY_ROUNDED", None) or getattr(Icons, "KEY", None),
        text_size=13,
    )

    chat_id_input = ft.TextField(
        label="Telegram Chat ID",
        value=saved_cfg.get("chat_id", ""),
        hint_text="例如: 123456789 或 @my_channel",
        border_radius=8,
        border_color="#30363d",
        focused_border_color="#11998e",
        prefix_icon=getattr(Icons, "SEND_ROUNDED", None) or getattr(Icons, "SEND", None),
        text_size=13,
    )

    proxy_input = ft.TextField(
        label="网络代理 (可选，用于 Telegram 直连)",
        value=saved_cfg.get("proxy", ""),
        hint_text="例如: http://127.0.0.1:7890 或 socks5://127.0.0.1:1080",
        border_radius=8,
        border_color="#30363d",
        focused_border_color="#11998e",
        prefix_icon=getattr(Icons, "SHIELD_OUTLINED", None) or getattr(Icons, "SHIELD", None),
        text_size=13,
    )

    keywords_input = ft.TextField(
        label="监控关键词",
        value=saved_cfg.get("keywords", "立正, 张三"),
        hint_text="输入待监控的词汇，支持中英文逗号、顿号或换行分隔（如：帮助，救命）",
        multiline=True,
        min_lines=2,
        max_lines=3,
        border_radius=8,
        border_color="#30363d",
        focused_border_color="#11998e",
        prefix_icon=getattr(Icons, "TAG_ROUNDED", None) or getattr(Icons, "TAG", None),
        text_size=13,
    )

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
                        ft.Text("系统配置", size=14, weight=ft.FontWeight.W_600, color="#e6edf3"),
                    ],
                ),
                token_input,
                chat_id_input,
                proxy_input,
                keywords_input,
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
            log_message("Error: 请先完整填写 Telegram Bot Token 和 Chat ID。")
            return

        raw_keywords = re.split(r"[,，、\n]+", keywords_val)
        keywords = [k.strip() for k in raw_keywords if k.strip()]

        if not keywords:
            log_message("Error: 请至少输入一个监控关键词。")
            return

        # Auto save user configuration
        save_user_config(token_val, chat_val, proxy_val or "", keywords_val)

        update_status_badge(True, "初始化中...")

        system_holder["instance"] = VoiceAlertSystem(
            bot_token=token_val,
            chat_id=chat_val,
            keywords=keywords,
            proxy=proxy_val,
            on_log=log_message,
            on_status_change=update_status_badge,
        )

        system_holder["instance"].start_detection()

    def stop_click(e):
        if system_holder["instance"]:
            system_holder["instance"].stop_detection()
        update_status_badge(False, "已停止")

    # Main Action Buttons
    play_icon = getattr(Icons, "PLAY_ARROW_ROUNDED", None) or getattr(Icons, "PLAY_ARROW", None)
    stop_icon = getattr(Icons, "STOP_ROUNDED", None) or getattr(Icons, "STOP", None)

    start_btn = ft.Container(
        content=ButtonControl(
            "开始监听",
            icon=play_icon,
            on_click=start_click,
            style=ft.ButtonStyle(
                color="#ffffff",
                bgcolor="#11998e",
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=make_padding(h=24, v=16),
            ),
        ),
        expand=True,
    )

    stop_btn = ft.Container(
        content=ButtonControl(
            "停止监听",
            icon=stop_icon,
            on_click=stop_click,
            disabled=True,
            style=ft.ButtonStyle(
                color="#ffffff",
                bgcolor="#da3633",
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=make_padding(h=24, v=16),
            ),
        ),
        expand=True,
    )

    actions_row = ft.Row(
        spacing=16,
        controls=[start_btn, stop_btn],
    )

    # Terminal Log Component
    log_counter_text = ft.Text("0 条记录", size=11, color="#8b949e")

    def clear_logs(e):
        log_lines.clear()
        refresh_log_view()

    def copy_logs(e):
        all_text = "\n".join(log_lines)
        safe_copy_clipboard(page, all_text)
        log_counter_text.value = "已复制到剪贴板!"
        page.update()
        def restore():
            time.sleep(2)
            log_counter_text.value = f"{len(log_lines)} 条记录"
            try:
                page.update()
            except Exception:
                pass
        threading.Thread(target=restore, daemon=True).start()

    copy_icon = getattr(Icons, "CONTENT_COPY_ROUNDED", None) or getattr(Icons, "COPY", None)
    clear_icon = getattr(Icons, "DELETE_SWEEP_OUTLINED", None) or getattr(Icons, "CLEAR", None)

    log_list_view = ft.ListView(
        spacing=4,
        auto_scroll=True,
        height=220,
    )

    terminal_header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(getattr(Icons, "TERMINAL_ROUNDED", None) or getattr(Icons, "TERMINAL", None), size=16, color="#58a6ff"),
                    ft.Text("实时监控日志", size=13, weight=ft.FontWeight.W_600, color="#e6edf3"),
                    log_counter_text,
                ],
            ),
            ft.Row(
                spacing=4,
                controls=[
                    ft.IconButton(icon=copy_icon, icon_size=16, icon_color="#8b949e", tooltip="复制日志", on_click=copy_logs),
                    ft.IconButton(icon=clear_icon, icon_size=16, icon_color="#8b949e", tooltip="清空日志", on_click=clear_logs),
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
            spacing=20,
            controls=[
                header_section,
                config_card,
                actions_row,
                terminal_card,
            ],
        ),
    )

    page.add(layout_wrapper)

    # Cleanup on exit
    def window_event(e):
        event_type = getattr(e, "data", "") or getattr(e, "type", "")
        if event_type in ("close", "WindowEventType.CLOSE"):
            if system_holder["instance"]:
                system_holder["instance"].stop_detection()
            close_window()

    configure_window()

if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)
