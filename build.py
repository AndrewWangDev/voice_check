import os
import shutil
import PyInstaller.__main__

# Define paths
APP_NAME = "VoiceAlert"
MAIN_SCRIPT = "gui.py"
OUTPUT_DIR = "release"
DIST_DIR = "dist"
BUILD_DIR = "build"

def build():
    print("Building EXE...")
    
    # 0. Ensure logo.ico is generated from logo.jpg for Windows icon embedding
    if os.path.exists("logo.jpg"):
        try:
            from PIL import Image
            img = Image.open("logo.jpg")
            img.save("logo.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            print("Successfully prepared logo.ico with multi-resolution icon sizes.")
        except Exception as e:
            print(f"Warning: Failed to create logo.ico: {e}")

    # 1. Clean previous builds
    if os.path.exists(OUTPUT_DIR):
        try:
            shutil.rmtree(OUTPUT_DIR)
        except Exception as e:
            print(f"Warning: Failed to clean {OUTPUT_DIR}: {e}")

    if os.path.exists(BUILD_DIR):
        try:
            shutil.rmtree(BUILD_DIR)
        except Exception as e:
            print(f"Warning: Failed to clean {BUILD_DIR}: {e}")
    
    # PyInstaller arguments
    pyi_args = [
        MAIN_SCRIPT,
        '--name=%s' % APP_NAME,
        '--onedir',
        '--windowed',  # Hide console
        '--noconfirm',
        '--clean',
        f'--distpath={OUTPUT_DIR}',
        f'--workpath={BUILD_DIR}',
        # Hidden imports
        '--hidden-import=vosk',
        '--hidden-import=pyaudio',
        '--hidden-import=requests',
        '--hidden-import=flet',
        '--hidden-import=flet_desktop',
        '--hidden-import=flet_desktop.version',
        '--hidden-import=flet_desktop.win_taskbar',
        # Collect Flet packages and data
        '--collect-all=flet',
        '--collect-all=flet_desktop',
        # Collect all vosk C-extensions, DLLs and data
        '--collect-all=vosk',
        # Embed logo assets
        f'--add-data=logo.jpg{os.pathsep}.',
    ]

    if os.path.exists("logo.ico"):
        pyi_args.extend([
            '--icon=logo.ico',
            f'--add-data=logo.ico{os.pathsep}.',
        ])

    # Exclude Tkinter and unused heavy GUI/Scientific packages
    pyi_args.extend([
        '--exclude-module=tkinter',
        '--exclude-module=_tkinter',
        '--exclude-module=customtkinter',
        '--exclude-module=ttkbootstrap',
        '--exclude-module=torch',
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        '--exclude-module=PySide6',
        '--exclude-module=pandas',
        '--exclude-module=cv2',
        '--exclude-module=IPython',
        '--exclude-module=jupyter',
    ])

    # 2. Run PyInstaller
    PyInstaller.__main__.run(pyi_args)
    
    # 3. Handle Assets & Model Copying
    exe_dir = os.path.join(OUTPUT_DIR, APP_NAME)
    internal_dir = os.path.join(exe_dir, "_internal")

    # Ensure vosk package with all DLLs exists in _internal\vosk for open_dll()
    try:
        import vosk
        vosk_src = os.path.dirname(vosk.__file__)
        vosk_dst = os.path.join(internal_dir, "vosk")
        print(f"Ensuring full vosk binaries in {vosk_dst}...")
        shutil.copytree(vosk_src, vosk_dst, dirs_exist_ok=True)
    except Exception as e:
        print(f"Warning: Failed to copy vosk directory: {e}")

    # Ensure flet_desktop package exists in _internal\flet_desktop
    try:
        import flet_desktop
        flet_desktop_src = os.path.dirname(flet_desktop.__file__)
        flet_desktop_dst = os.path.join(internal_dir, "flet_desktop")
        print(f"Ensuring flet_desktop in {flet_desktop_dst}...")
        shutil.copytree(flet_desktop_src, flet_desktop_dst, dirs_exist_ok=True)
    except Exception as e:
        print(f"Warning: Failed to copy flet_desktop package: {e}")

    # Ensure standalone flet_view runtime binary exists in _internal\flet_view
    try:
        import flet_desktop
        import sys
        from pathlib import Path
        client_dir = flet_desktop.ensure_client_cached()
        flet_client_src = Path(client_dir) / "flet"
        has_client = False
        if flet_client_src.exists():
            if sys.platform == "win32":
                has_client = (flet_client_src / "flet.exe").exists()
            elif sys.platform == "darwin":
                has_client = (flet_client_src / "flet").exists() or any(flet_client_src.glob("*.app"))
            else:  # Linux / Unix
                has_client = (flet_client_src / "flet").exists()

        if has_client:
            flet_view_dst = os.path.join(internal_dir, "flet_view")
            print(f"Bundling standalone Flet View client into {flet_view_dst}...")
            shutil.copytree(str(flet_client_src), flet_view_dst, dirs_exist_ok=True)
            print("Successfully bundled Flet View client.")
        else:
            print(f"Warning: Flet View executable not found in {flet_client_src}")
    except Exception as e:
        print(f"Warning: Failed to bundle flet_view client: {e}")
    
    # Copy logo files to release directory
    for logo_name in ["logo.jpg", "logo.ico"]:
        if os.path.exists(logo_name):
            try:
                shutil.copy2(logo_name, os.path.join(exe_dir, logo_name))
                print(f"Copied {logo_name} to release folder.")
            except Exception as e:
                print(f"Warning: Failed to copy {logo_name}: {e}")

    model_name = "vosk-model-small-cn-0.22"
    if os.path.exists(model_name):
        print(f"Copying model {model_name} to release folder...")
        shutil.copytree(model_name, os.path.join(exe_dir, model_name), dirs_exist_ok=True)
    else:
        print("Model not found locally. It will be downloaded on first run by the app.")

    print(f"Build complete. Application is in {exe_dir}")

if __name__ == "__main__":
    build()
