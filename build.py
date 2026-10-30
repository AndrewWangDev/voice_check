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
        # Collect Flet data files (e.g. controls/material/icons.json)
        '--collect-data=flet',
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
