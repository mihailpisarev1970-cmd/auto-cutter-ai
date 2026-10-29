<div align="center">

# 🎬 Auto Cutter AI

### Умный видеокомбайн: скачивание, кадрирование 9:16, AI-нарезка Shorts, караоке-субтитры и уникализация

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Gradio](https://img.shields.io/badge/Gradio-UI-FF7C00?style=for-the-badge)](https://www.gradio.app/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-video%20processing-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Whisper](https://img.shields.io/badge/OpenAI-Whisper-412991?style=for-the-badge&logo=openai&logoColor=white)](https://github.com/openai/whisper)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-downloader-red?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Face%20Detection-0097A7?style=for-the-badge)](https://mediapipe.dev/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](#лицензия)

**Загрузите ссылку или файл — получите готовый вертикальный ролик с субтитрами, автокропом и уникализацией.**

[Возможности](#возможности) • [Архитектура](#архитектура) • [Установка](#установка) • [Использование](#использование) • [Стек](#стек-технологий)

</div>

---

## О проекте

**Auto Cutter AI** — это локальное Gradio-приложение для автоматизации производства коротких видео. Проект объединяет в себе скачивание, нарезку, умное кадрирование и уникализацию в одном интерфейсе. 

Приложение рассчитано на локальный запуск на Windows/Linux/macOS. Для работы нужны **Python**, **FFmpeg** и API-ключ **Polza AI** (для вкладки с искусственным интеллектом).

---

## Возможности

| Возможность | Описание |
|---|---|
| ⚡ **Скачивание видео** | Поддержка YouTube, VK, Rutube и других сайтов через `yt-dlp` |
| ✂️ **Быстрая нарезка** | Скачивание целого видео или конкретного отрезка по таймкодам |
| 📱 **Конвертация 16:9 → 9:16** | Три режима кадрирования: статичный кроп, размытый фон, умный автокроп |
| 🤖 **AI-нарезка Shorts** | Whisper + LLM через Polza AI автоматически выбирают цельный смысловой фрагмент |
| 🎤 **Караоке-субтитры** | Генерация ASS-субтитров с подсветкой слов через Whisper |
| 🧬 **Уникализация** | Микро-изменение скорости, кропа, цвета, шума и аудио для обхода теневых банов |
| 🖥️ **Gradio UI** | Удобный веб-интерфейс с тремя вкладками для всех задач |

<details>
<summary><b>Подробнее о режимах кадрирования</b></summary>

| Режим | Что делает |
|---|---|
| `full` | Полностью заполняет вертикальный кадр, статично обрезая края |
| `blur` | Помещает видео на размытый фон с полосами |
| `autotrack` | Ищет лицо спикера через MediaPipe и выбирает среднюю позицию кропа |

</details>

<details>
<summary><b>Подробнее об уникализации</b></summary>

В финальном рендере могут применяться:
- случайное микро-ускорение видео;
- лёгкий кроп и масштабирование;
- фильтр `unsharp` для компенсации резкости;
- микро-коррекция контраста, яркости и насыщенности;
- минимальный шум;
- изменение темпа аудио и частоты дискретизации;
- очистка метаданных;
- флаг `faststart` для быстрого старта воспроизведения.

</details>

---

## Архитектура

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
---


## Возможности
