import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Polza AI Gateway & LLM
POLZA_API_KEY = os.getenv("POLZA_API_KEY", "").strip()
POLZA_BASE_URL = os.getenv("POLZA_BASE_URL", "https://polza.ai/api/v1").strip()
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "").strip()

# Динамическая загрузка списка моделей из .env
_models_json = os.getenv("AVAILABLE_LLM_MODELS", "[]")
try:
    _parsed = json.loads(_models_json)
    LLM_CHOICES = [(item.get("label", item.get("value")), item.get("value")) for item in _parsed]
except Exception:
    LLM_CHOICES = []

if not DEFAULT_LLM_MODEL and LLM_CHOICES:
    DEFAULT_LLM_MODEL = LLM_CHOICES[0][1]

# Whisper Settings
WHISPER_BASE_MODEL = os.getenv("WHISPER_BASE_MODEL", "base").strip()
WHISPER_SUBTITLES_MODEL = os.getenv("WHISPER_SUBTITLES_MODEL", "small").strip()

# Video & Subtitles
TARGET_WIDTH = int(os.getenv("TARGET_WIDTH", 1080))
TARGET_HEIGHT = int(os.getenv("TARGET_HEIGHT", 1920))
SUBTITLE_FONT_SIZE = int(os.getenv("SUBTITLE_FONT_SIZE", 64))
SUBTITLE_MARGIN_V = int(os.getenv("SUBTITLE_MARGIN_V", 440))


def get_default_desktop_dir() -> str:
    desktop = Path.home() / "Desktop"
    return str(desktop) if desktop.exists() else str(Path.cwd())


def get_default_desktop_path(filename="final_clip.mp4") -> str:
    return str(Path(get_default_desktop_dir()) / filename)