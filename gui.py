import re
import flet as ft
from main import VoiceAlertSystem

# Cross-version compatibility aliases for modern Flet (0.25+ / 0.80+ / 1.0) and legacy Flet
Colors = getattr(ft, "Colors", getattr(ft, "colors", None))
Icons = getattr(ft, "Icons", getattr(ft, "icons", None))
ButtonControl = getattr(ft, "Button", getattr(ft, "ElevatedButton", None))

def make_border(color):
    """Safely creates a border across different Flet versions."""
    if hasattr(ft, "Border") and hasattr(ft.Border, "all"):
        return ft.Border.all(1, color)
    elif hasattr(ft, "border") and hasattr(ft.border, "all"):
        return ft.border.all(1, color)
    return None

def main(page: ft.Page):
    page.title = "Voice Alert - Configuration & Monitor"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 20

    # Cross-version desktop window configuration helper
    def configure_window():
        target_width = 460
        target_height = 720
        # Modern Flet (0.25+ / 0.86+)
        if hasattr(page, "window") and page.window is not None:
            try:
                page.window.width = target_width
                page.window.height = target_height
                page.window.prevent_close = True
                page.window.on_event = window_event
                return
            except Exception:
                pass
        # Legacy Flet (< 0.25)
        try:
            page.window_width = target_width
            page.window_height = target_height
            page.window_prevent_close = True
            page.on_window_event = window_event
        except Exception:
            pass

    def close_window():
        # Modern Flet
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
        # Legacy Flet
        if hasattr(page, "window_destroy"):
            try:
                page.window_destroy()
            except Exception:
                pass

    # State holder for the system
    system_holder = {"instance": None}

    # Bounded log buffer to prevent unbounded memory growth
    log_lines = []
    MAX_LOG_LINES = 200

    def log_message(message):
        log_lines.append(str(message))
        if len(log_lines) > MAX_LOG_LINES:
            del log_lines[: len(log_lines) - MAX_LOG_LINES]
        log_text.value = "\n".join(log_lines)
        try:
            page.update()
            log_column.scroll_to(offset=-1, duration=200)
        except Exception:
            pass

    def on_status_change(running, msg):
        status_text.value = f"Status: {msg}"
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

    # Input Fields
    token_input = ft.TextField(
        label="Telegram Bot Token", 
        password=True, 
        can_reveal_password=True,
        hint_text="Enter your Bot Token"
    )
    
    chat_id_input = ft.TextField(
        label="Chat ID", 
        hint_text="Enter your Chat ID"
    )

    proxy_input = ft.TextField(
        label="Proxy (Optional)",
        hint_text="e.g. http://127.0.0.1:7890 or socks5://127.0.0.1:1080"
    )
    
    keywords_input = ft.TextField(
        label="Keywords", 
        value="立正, 张三",
        hint_text="逗号分隔（支持中英文逗号与换行，如：立正，张三）",
        multiline=True,
        min_lines=1,
        max_lines=3
    )

    # Status & Log
    status_text = ft.Text("Status: Idle", size=16, weight=ft.FontWeight.BOLD)
    
    log_text = ft.Text(value="", size=12, font_family="Consolas")
    log_column = ft.Column([log_text], scroll=ft.ScrollMode.AUTO, height=200)
    
    outline_color = getattr(Colors, "OUTLINE", "outline") if Colors else "outline"
    log_container = ft.Container(
        content=log_column,
        border=make_border(outline_color),
        border_radius=10,
        padding=10,
        expand=True
    )

    def start_click(e):
        if not token_input.value or not chat_id_input.value:
            log_message("Error: Token and Chat ID are required.")
            return

        # Parse keywords supporting Chinese and English commas, ideographic commas, and newlines
        raw_keywords = re.split(r'[,，、\n]+', (keywords_input.value or "").strip())
        keywords = [k.strip() for k in raw_keywords if k.strip()]
        
        if not keywords:
            log_message("Error: At least one keyword is required.")
            return

        proxy = (proxy_input.value or "").strip() or None

        # Update UI to initializing state
        on_status_change(True, "Starting...")

        # Initialize System
        system_holder["instance"] = VoiceAlertSystem(
            bot_token=token_input.value.strip(),
            chat_id=chat_id_input.value.strip(),
            keywords=keywords,
            proxy=proxy,
            on_log=log_message,
            on_status_change=on_status_change
        )
        
        system_holder["instance"].start_detection()

    def stop_click(e):
        if system_holder["instance"]:
            system_holder["instance"].stop_detection()
        on_status_change(False, "Stopped")

    primary_color = getattr(Colors, "PRIMARY", "primary") if Colors else "primary"
    on_primary_color = getattr(Colors, "ON_PRIMARY", "on_primary") if Colors else "on_primary"
    error_color = getattr(Colors, "ERROR", "error") if Colors else "error"
    on_error_color = getattr(Colors, "ON_ERROR", "on_error") if Colors else "on_error"
    play_icon = getattr(Icons, "PLAY_ARROW", None) if Icons else None
    stop_icon = getattr(Icons, "STOP", None) if Icons else None

    start_btn = ButtonControl(
        "开始检测", 
        icon=play_icon, 
        on_click=start_click,
        style=ft.ButtonStyle(
            color=on_primary_color,
            bgcolor=primary_color,
        )
    )

    stop_btn = ButtonControl(
        "结束检测", 
        icon=stop_icon, 
        on_click=stop_click,
        disabled=True,
        style=ft.ButtonStyle(
            color=on_error_color,
            bgcolor=error_color, 
        )
    )

    transparent_color = getattr(Colors, "TRANSPARENT", "transparent") if Colors else "transparent"

    # Layout
    page.add(
        ft.Column(
            [
                ft.Text("Configuration", size=20, weight=ft.FontWeight.BOLD),
                token_input,
                chat_id_input,
                proxy_input,
                keywords_input,
                ft.Divider(),
                ft.Row([start_btn, stop_btn], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=10, color=transparent_color),
                status_text,
                ft.Text("Logs:", size=14),
                log_container,
            ],
            expand=True,
        )
    )

    # Cleanup on exit
    def window_event(e):
        # Support both e.data == "close" and WindowEventType.CLOSE
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
