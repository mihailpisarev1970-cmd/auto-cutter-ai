import os
import subprocess
import yt_dlp
import gradio as gr
from utils import parse_time_str


def get_base_ydl_opts(custom_opts=None):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        # Заставляем yt-dlp притворяться официальными мобильными клиентами YouTube
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios"],
                "player_skip": ["webpage", "configs"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "com.google.android.youtube/19.29.37 "
                "(Linux; U; Android 14; US) gzip"
            )
        },
    }
    # Если локальный файл cookies.txt всё-таки присутствует — подхватываем его
    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"

    if custom_opts:
        opts.update(custom_opts)
    return opts


def download_video_stream(url: str, output_path: str):
    ydl_opts = get_base_ydl_opts({
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_path,
        "overwrites": True,
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
    })
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url.strip()])
    except Exception as e:
        raise gr.Error(f"Ошибка при скачивании видео: {e}")


def download_or_cut_stream(
    url: str,
    mode: str,
    start_time: str,
    end_time: str,
    output_path: str,
    progress=gr.Progress(),
):
    if not url or not url.strip().startswith(("http://", "https://")):
        raise gr.Error("Укажите корректную ссылку на видео (YouTube / VK / Rutube)!")

    final_target = output_path.strip().strip('"').strip("'")
    if not final_target.endswith(".mp4"):
        final_target += ".mp4"
    os.makedirs(os.path.dirname(os.path.abspath(final_target)), exist_ok=True)

    if mode == "full":
        progress(0.3, desc="Загрузка видео в оригинальном формате...")
        download_video_stream(url, final_target)
        progress(1.0, desc="Готово!")
        return final_target, f"Оригинальное видео сохранено в:\n{final_target}"

    progress(0.2, desc="Извлечение потоков...")
    ydl_opts = get_base_ydl_opts({
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url.strip(), download=False)
    except Exception as e:
        raise gr.Error(f"Не удалось получить данные о видео: {e}")

    video_url = None
    audio_url = None

    if "requested_formats" in info and len(info["requested_formats"]) >= 2:
        video_url = info["requested_formats"][0]["url"]
        audio_url = info["requested_formats"][1]["url"]
    else:
        video_url = info.get("url")

    if not video_url:
        raise gr.Error("Не удалось получить прямые потоки видео.")

    ss_sec = parse_time_str(start_time)
    to_sec = parse_time_str(end_time)

    if to_sec <= ss_sec:
        raise gr.Error("Время окончания должно быть больше времени начала!")

    duration = to_sec - ss_sec
    progress(0.4, desc=f"Вырезание оригинального отрезка {start_time} - {end_time}...")

    cmd = ["ffmpeg", "-y"]
    if audio_url:
        cmd.extend([
            "-ss", str(ss_sec), "-t", str(duration), "-i", video_url,
            "-ss", str(ss_sec), "-t", str(duration), "-i", audio_url,
            "-map", "0:v:0", "-map", "1:a:0",
        ])
    else:
        cmd.extend([
            "-ss", str(ss_sec), "-t", str(duration), "-i", video_url,
        ])

    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-avoid_negative_ts", "make_zero",
        final_target,
    ])
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    progress(1.0, desc="Готово!")
    return final_target, f"Оригинальный отрезок сохранен в:\n{final_target}"