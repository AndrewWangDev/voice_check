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
    
    # 2. Run PyInstaller
    PyInstaller.__main__.run([
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
        # Collect Flet data files (e.g. controls/material/icons.json)
        '--collect-data=flet',
        # Embed logo asset
        '--add-data=logo.jpg;.',
        # Exclude Tkinter and unused heavy GUI/Scientific packages to prevent pyi_rth__tkinter error
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
    
    # 3. Handle Assets & Model Copying
    exe_dir = os.path.join(OUTPUT_DIR, APP_NAME)
    
    # Copy logo if present
    if os.path.exists("logo.jpg"):
        try:
            shutil.copy2("logo.jpg", os.path.join(exe_dir, "logo.jpg"))
            print("Copied logo.jpg to release folder.")
        except Exception as e:
            print(f"Warning: Failed to copy logo.jpg: {e}")

    model_name = "vosk-model-small-cn-0.22"
    if os.path.exists(model_name):
        print(f"Copying model {model_name} to release folder...")
        shutil.copytree(model_name, os.path.join(exe_dir, model_name), dirs_exist_ok=True)
    else:
        print("Model not found locally. It will be downloaded on first run by the app.")

    print(f"Build complete. Application is in {exe_dir}")

if __name__ == "__main__":
    build()
