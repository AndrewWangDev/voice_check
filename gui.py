import flet as ft
from main import VoiceAlertSystem

def main(page: ft.Page):
    page.title = "Voice Alert - Configuration & Monitor"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.window_width = 450
    page.window_height = 700
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 20

    # Logging function to update UI
    def log_message(message):
        log_text.value += f"{message}\n"
        page.update()
        # Auto-scroll to bottom
        log_column.scroll_to(offset=-1, duration=300)

    # State holder for the system
    # We use a mutable list to hold the instance so we can modify it inside closures
    system_holder = {"instance": None}

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
    
    keywords_input = ft.TextField(
        label="Keywords", 
        value="立正, 张三",
        hint_text="Comma separated (e.g. 立正, 张三)",
        multiline=True,
        min_lines=1,
        max_lines=3
    )

    # Status & Log
    status_text = ft.Text("Status: Idle", size=16, weight=ft.FontWeight.BOLD)
    
    log_text = ft.Text(value="", size=12, font_family="Consolas")
    log_column = ft.Column([log_text], scroll=ft.ScrollMode.AUTO, height=200)
    log_container = ft.Container(
        content=log_column,
        border=ft.border.all(1, ft.colors.OUTLINE),
        border_radius=10,
        padding=10,
        expand=True
    )

    def start_click(e):
        if not token_input.value or not chat_id_input.value:
            log_message("Error: Token and Chat ID are required.")
            return

        # Parse keywords
        raw_keywords = keywords_input.value.split(",")
        keywords = [k.strip() for k in raw_keywords if k.strip()]
        
        if not keywords:
            log_message("Error: At least one keyword is required.")
            return

        # Disable inputs during run
        token_input.disabled = True
        chat_id_input.disabled = True
        keywords_input.disabled = True
        start_btn.disabled = True
        stop_btn.disabled = False
        
        # Initialize System
        system_holder["instance"] = VoiceAlertSystem(
            bot_token=token_input.value,
            chat_id=chat_id_input.value,
            keywords=keywords,
            on_log=log_message
        )
        
        system_holder["instance"].start_detection()
        status_text.value = "Status: Running"
        page.update()

    def stop_click(e):
        if system_holder["instance"]:
            system_holder["instance"].stop_detection()
        
        status_text.value = "Status: Stopped"
        
        # Re-enable inputs
        token_input.disabled = False
        chat_id_input.disabled = False
        keywords_input.disabled = False
        start_btn.disabled = False
        stop_btn.disabled = True
        page.update()

    start_btn = ft.ElevatedButton(
        "开始检测", 
        icon=ft.icons.PLAY_ARROW, 
        on_click=start_click,
        style=ft.ButtonStyle(
            color=ft.colors.ON_PRIMARY,
            bgcolor=ft.colors.PRIMARY,
        )
    )

    stop_btn = ft.ElevatedButton(
        "结束检测", 
        icon=ft.icons.STOP, 
        on_click=stop_click,
        disabled=True,
        style=ft.ButtonStyle(
            color=ft.colors.ON_ERROR,
            bgcolor=ft.colors.ERROR, 
        )
    )

    # Layout
    page.add(
        ft.Column(
            [
                ft.Text("Configuration", size=20, weight=ft.FontWeight.BOLD),
                token_input,
                chat_id_input,
                keywords_input,
                ft.Divider(),
                ft.Row([start_btn, stop_btn], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                status_text,
                ft.Text("Logs:", size=14),
                log_container,
            ],
            expand=True,
        )
    )

    # Cleanup on exit
    def window_event(e):
        if e.data == "close":
            if system_holder["instance"]:
                system_holder["instance"].stop_detection()
            page.window_destroy()

    page.window_prevent_close = True
    page.on_window_event = window_event

if __name__ == "__main__":
    ft.app(target=main)
