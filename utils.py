import os
import tkinter as tk
from tkinter import filedialog
from config import get_default_desktop_dir

def parse_time_str(time_str: str) -> float:
    time_str = str(time_str).strip()
    if not time_str:
        return 0.0
    parts = time_str.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return 0.0
    return 0.0

def open_folder_dialog(current_path: str, default_filename: str) -> str:
    try:
        root = tk.Tk()
        root.attributes("-topmost", True)
        root.withdraw()

        initial_dir = (
            os.path.dirname(current_path)
            if current_path
            else get_default_desktop_dir()
        )
        selected_folder = filedialog.askdirectory(
            initialdir=initial_dir, title="Выберите папку для сохранения видео"
        )
        root.destroy()

        if selected_folder:
            filename = (
                os.path.basename(current_path)
                if current_path
                else default_filename
            )
            if not filename.endswith(".mp4"):
                filename = default_filename
            return os.path.join(os.path.normpath(selected_folder), filename)
    except Exception:
        pass
    return current_path