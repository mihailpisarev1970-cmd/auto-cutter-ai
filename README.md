<div align="center">

# 🎬 Auto Cutter AI

### Умный видеокомбайн: скачивание, кадрирование 9:16, AI-нарезка Shorts, караоке-субтитры и уникализация

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Gradio](https://img.shields.io/badge/Gradio-UI-FF7C00?style=for-the-badge)](https://www.gradio.app/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-video%20processing-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Whisper](https://img.shields.io/badge/OpenAI-Whisper-412991?style=for-the-badge&logo=openai&logoColor=white)](https://github.com/openai/whisper)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-downloader-red?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Face%20Detection-0097A7?style=for-the-badge)](https://mediapipe.dev/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](#license)

**Загрузите ссылку или файл — получите готовый вертикальный ролик с субтитрами, автокропом и уникализацией.**

[Возможности](#features) • [Архитектура](#architecture) • [Установка](#installation) • [Использование](#usage) • [Стек](#stack)

</div>

---

<a id="features"></a>
## 📖 О проекте

**Auto Cutter AI** — это локальное Gradio-приложение для автоматизации производства коротких видео.

Проект объединяет несколько сценариев в одном интерфейсе:

- скачивание видео по ссылке;
- быстрая нарезка по таймкодам;
- преобразование горизонтального видео `16:9` в вертикальное `9:16`;
- умный автокроп с определением лица спикера;
- AI-поиск цельного фрагмента для Shorts/Reels;
- генерация караоке-субтитров через Whisper;
- уникализация видео и аудио через FFmpeg-фильтры.

Приложение рассчитано на локальный запуск на Windows/Linux/macOS. Для работы нужны **Python**, **FFmpeg** и API-ключ **Polza AI** для AI-нарезки.

### ✨ Возможности

| Возможность | Описание |
|---|---|
| ⚡ Скачивание видео | YouTube, VK, Rutube и другие сайты, поддерживаемые `yt-dlp` |
| ✂️ Быстрая нарезка | Скачивание целого видео или конкретного отрезка по таймкодам |
| 📱 Конвертация 16:9 → 9:16 | Три режима кадрирования: полный кроп, размытый фон, автокроп по лицу |
| 🤖 AI-нарезка Shorts | Whisper + LLM через Polza AI выбирают цельный смысловой фрагмент |
| 🎤 Караоке-субтитры | Генерация ASS-субтитров по словам через Whisper |
| 🧬 Уникализация | Микро-изменение скорости, кропа, цвета, шума и аудио |
| 🖥️ Gradio UI | Три вкладки: скачивание, конвертация, AI-нарезка |
| 📁 Сохранение на диск | Выбор папки и имени итогового файла |

---

<a id="architecture"></a>
## 🏗 Архитектура

```mermaid
flowchart TD
    UI[Gradio UI<br/>app.py] --> DL[downloader.py<br/>yt-dlp + FFmpeg]
    UI --> VP[video_processor.py<br/>16:9 → 9:16]
    UI --> AI[ai_pipeline.py<br/>AI-нарезка]

    DL --> YT[yt-dlp]
    DL --> FF[FFmpeg]

    VP --> MP[MediaPipe Face Detection]
    VP --> FF
    VP --> SUB[subtitles.py]

    AI --> WH[Whisper]
    AI --> LLM[Polza AI<br/>OpenAI-compatible API]
    AI --> SUB
    AI --> FF

    SUB --> ASS[ASS-субтитры]
    ASS --> FF
