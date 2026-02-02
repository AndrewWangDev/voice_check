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
        shutil.rmtree(OUTPUT_DIR)
    
    # 2. Run PyInstaller
    PyInstaller.__main__.run([
        MAIN_SCRIPT,
        '--name=%s' % APP_NAME,
        '--windowed',  # Hide console
        '--noconfirm',
        '--clean',
        f'--distpath={OUTPUT_DIR}',
        f'--workpath={BUILD_DIR}',
        # Add hidden imports if necessary
        '--hidden-import=vosk',
        '--hidden-import=pyaudio',
        '--hidden-import=requests',
    ])
    
    # 3. Handle Model Copying
    exe_dir = os.path.join(OUTPUT_DIR, APP_NAME)
    model_name = "vosk-model-small-cn-0.22"
    
    if os.path.exists(model_name):
        print(f"Copying model {model_name} to release folder...")
        shutil.copytree(model_name, os.path.join(exe_dir, model_name))
    else:
        print("Model not found locally. It will be downloaded on first run by the app.")

    print(f"Build complete. Application is in {exe_dir}")

if __name__ == "__main__":
    build()
