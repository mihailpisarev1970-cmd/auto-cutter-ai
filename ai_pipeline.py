import json
import os
import random
import re
import subprocess
from typing import List, Dict, Any, Tuple
import whisper
from openai import OpenAI
import gradio as gr
from config import (
    POLZA_API_KEY,
    POLZA_BASE_URL,
    TARGET_WIDTH,
    TARGET_HEIGHT,
    WHISPER_BASE_MODEL,
    WHISPER_SUBTITLES_MODEL,
    LLM_CHOICES,
)
from downloader import download_video_stream
from subtitles import create_karaoke_ass
from video_processor import get_speaker_center_crop_filter, has_audio_stream


def extract_meaningful_chunks(raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Группирует мелкие фразы Whisper в цельные смысловые блоки для анализа LLM."""
    if not raw_segments:
        return []
    total_duration = raw_segments[-1]["end"]
    if total_duration > 3600:
        chunk_window = 22.0
    elif total_duration > 1500:
        chunk_window = 14.0
    elif total_duration > 600:
        chunk_window = 8.0
    else:
        chunk_window = 5.0

    prepared_segments = []
    cur_start = raw_segments[0]["start"]
    cur_end = raw_segments[0]["end"]
    cur_text = [raw_segments[0]["text"].strip()]

    for s in raw_segments[1:]:
        clean_text = s["text"].strip()
        if not clean_text:
            continue
        if (s["end"] - cur_start) < chunk_window:
            cur_end = s["end"]
            cur_text.append(clean_text)
        else:
            prepared_segments.append({
                "start": round(cur_start, 2),
                "end": round(cur_end, 2),
                "text": " ".join(cur_text),
            })
            cur_start = s["start"]
            cur_end = s["end"]
            cur_text = [clean_text]

    if cur_text and " ".join(cur_text).strip():
        prepared_segments.append({
            "start": round(cur_start, 2),
            "end": round(cur_end, 2),
            "text": " ".join(cur_text),
        })
    return prepared_segments


def enforce_clip_duration(
    clips: List[Dict[str, Any]],
    raw_segments: List[Dict[str, Any]],
    total_duration: float,
    min_dur: int,
    max_dur: int,
) -> List[Dict[str, Any]]:
    """Гарантирует, что хронометраж лежит строго в границах [min_dur, max_dur]."""
    if not clips:
        end_time = min(float(max_dur), total_duration)
        return [{"start": 0.0, "end": round(end_time, 2), "reason": "Резервный отрезок"}]

    clip = clips[0]
    start_t = clip["start"]
    end_t = clip["end"]
    cur_dur = end_t - start_t

    if cur_dur > max_dur:
        for seg in reversed(raw_segments):
            if seg["start"] >= start_t and (seg["end"] - start_t) <= max_dur:
                end_t = seg["end"]
                break
        else:
            end_t = start_t + max_dur

    cur_dur = end_t - start_t
    if cur_dur < min_dur:
        for seg in raw_segments:
            if seg["end"] > end_t:
                end_t = seg["end"]
                if (end_t - start_t) >= min_dur:
                    break

        if (end_t - start_t) < min_dur:
            for seg in reversed(raw_segments):
                if seg["start"] < start_t:
                    start_t = seg["start"]
                    if (end_t - start_t) >= min_dur:
                        break

    start_t = max(0.0, start_t)
    end_t = min(total_duration, end_t)

    if total_duration <= min_dur:
        start_t = 0.0
        end_t = total_duration

    return [{
        "start": round(start_t, 2),
        "end": round(end_t, 2),
        "reason": clip.get("reason", "Выбранный логический отрезок"),
    }]


def query_polza_ai(
    prepared_segments: List[Dict[str, Any]],
    selected_model: str,
    min_dur: int,
    max_dur: int,
    total_duration: float,
) -> List[Dict[str, Any]]:
    """Обращается к Polza AI Gateway через выбранную модель."""
    if not POLZA_API_KEY:
        raise gr.Error("Не найден POLZA_API_KEY в файле .env!")

    client = OpenAI(base_url=POLZA_BASE_URL, api_key=POLZA_API_KEY, timeout=120.0)
    prompt = f"""
Ты — профессиональный видеомонтажер Shorts, Reels и подкастов.
Перед тобой транскрипт видео с таймкодами:
{json.dumps(prepared_segments, ensure_ascii=False)}

КРИТИЧЕСКИ ВАЖНЫЕ ТРЕБОВАНИЯ:
1. ХРОНОМЕТРАЖ: Длительность отрезка (end - start) СТРОГО ОБЯЗАНА быть от {min_dur} до {max_dur} секунд!
   - Запрещено возвращать отрезок короче {min_dur} секунд!
   - Если сцена короткая, объедини её со следующим текстом, чтобы уложиться в диапазон от {min_dur} до {max_dur} секунд.
2. ЗАВЕРШЕННОСТЬ: Фраза НЕ ДОЛЖНА обрываться на полуслове!
3. Найди 1 непрерывный цельный фрагмент.

Верни результат СТРОГО в JSON:
{{
  "genre": "юмор / экспертный / сторителлинг",
  "clips": [
    {{"start": 12.0, "end": 85.0, "reason": "Завершенное рассуждение"}}
  ]
}}
"""
    models_to_try = [selected_model]
    for _, model_val in LLM_CHOICES:
        if model_val not in models_to_try:
            models_to_try.append(model_val)

    for model_name in models_to_try:
        try:
            call_kwargs = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
            }
            if "gpt-" in model_name or "openai/" in model_name:
                call_kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**call_kwargs)
            content = response.choices[0].message.content.strip()

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                candidate_clips = data.get("clips", [])
                if candidate_clips:
                    return candidate_clips
        except Exception as e:
            print(f"[!] Ошибка вызова модели {model_name}: {e}. Пробуем следующую...")
            continue

    return []


def build_uniqualize_filters() -> Tuple[str, str]:
    """Генерирует нативные FFmpeg-фильтры уникализации."""
    speed = round(random.uniform(1.02, 1.035), 3)
    pts = round(1.0 / speed, 4)
    crop_factor = round(random.uniform(0.96, 0.98), 3)
    contrast = round(random.uniform(1.01, 1.025), 2)
    brightness = round(random.uniform(0.005, 0.012), 3)
    saturation = round(random.uniform(1.02, 1.04), 2)
    noise_lvl = random.randint(1, 2)
    sample_shift = round(random.uniform(1.005, 1.012), 3)

    v_filter = (
        f"crop=in_w*{crop_factor}:in_h*{crop_factor},"
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},"
        f"unsharp=3:3:0.5:3:3:0.0,"
        f"eq=contrast={contrast}:brightness={brightness}:saturation={saturation},"
        f"noise=alls={noise_lvl}:allf=t+u,"
        f"setpts={pts}*PTS"
    )

    a_filter = (
        f"atempo={speed},"
        f"asetrate=44100*{sample_shift},"
        f"aresample=44100"
    )
    return v_filter, a_filter


def process_video_pipeline(
    url_source: str,
    local_file: Any,
    output_path: str,
    selected_model: str,
    crop_mode: str,
    enable_subtitles: bool,
    min_dur: int,
    max_dur: int,
    enable_uniqualize: bool = True,
    progress=gr.Progress(),
):
    min_dur = int(min_dur)
    max_dur = int(max_dur)
    if min_dur > max_dur:
        min_dur, max_dur = max_dur, min_dur

    progress(0.05, desc="Подготовка источника видео...")
    video_path = ""
    downloaded_temp = False

    if url_source and url_source.strip().startswith(("http://", "https://")):
        video_path = "temp_downloaded_src.mp4"
        download_video_stream(url_source, video_path)
        downloaded_temp = True
    elif local_file is not None:
        video_path = local_file if isinstance(local_file, str) else local_file.name
    else:
        raise gr.Error("Укажите ссылку или загрузите видеофайл!")

    progress(0.20, desc=f"Анализ речи через Whisper ({WHISPER_BASE_MODEL})...")
    whisper_model = whisper.load_model(WHISPER_BASE_MODEL)

    transcribe_res = whisper_model.transcribe(
        video_path,
        temperature=(0.0, 0.2),
        condition_on_previous_text=False,
    )

    all_segments = transcribe_res.get("segments", [])
    raw_segments = [s for s in all_segments if s.get("text", "").strip()]

    if all_segments:
        total_duration = all_segments[-1]["end"]
    else:
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        try:
            res_dur = subprocess.run(probe_cmd, capture_output=True, text=True)
            total_duration = float(res_dur.stdout.strip())
        except Exception:
            total_duration = float(max_dur)

    if raw_segments:
        prepared_segments = extract_meaningful_chunks(raw_segments)
        progress(0.40, desc=f"Поиск фрагментов [{min_dur}–{max_dur} сек] через {selected_model}...")
        candidate_clips = query_polza_ai(
            prepared_segments, selected_model, min_dur, max_dur, total_duration
        )
        clips = enforce_clip_duration(
            candidate_clips, raw_segments, total_duration, min_dur, max_dur
        )
    else:
        clips = [{
            "start": 0.0,
            "end": min(float(max_dur), total_duration),
            "reason": "Вводный отрезок"
        }]

    actual_duration = round(clips[0]["end"] - clips[0]["start"], 1)
    progress(0.60, desc=f"Кадрирование 9:16 ({actual_duration} сек)...")
    temp_parts = []
    has_audio = has_audio_stream(video_path)

    for i, clip in enumerate(clips):
        part_name = f"temp_cut_{i}.mp4"
        temp_parts.append(part_name)

        padded_start = max(0.0, clip["start"] - 0.1)
        padded_end = min(total_duration, clip["end"] + 0.2)
        dur = max(1.0, padded_end - padded_start)

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{padded_start:.3f}",
            "-i", video_path,
            "-t", f"{dur:.3f}",
        ]

        if crop_mode == "full":
            v_filter = f"scale=-2:{TARGET_HEIGHT},crop={TARGET_WIDTH}:{TARGET_HEIGHT}:(in_w-{TARGET_WIDTH})/2:0,format=yuv420p"
            cmd.extend(["-vf", v_filter, "-map", "0:v:0"])
        elif crop_mode == "autotrack":
            v_filter = get_speaker_center_crop_filter(video_path, dur)
            cmd.extend(["-vf", f"{v_filter},format=yuv420p", "-map", "0:v:0"])
        else:
            filter_blur = (
                f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},boxblur=20:2[bg];"
                f"[0:v]scale={TARGET_WIDTH}:-2[fg];"
                f"[bg][fg]overlay=0:(H-h)/2,format=yuv420p[outv]"
            )
            cmd.extend(["-filter_complex", filter_blur, "-map", "[outv]"])

        if has_audio:
            fade_out_start = max(0.0, dur - 0.15)
            audio_filter = f"afade=t=in:ss=0:d=0.08,afade=t=out:st={fade_out_start:.2f}:d=0.15"
            cmd.extend(["-af", audio_filter, "-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k"])
        else:
            cmd.extend(["-an"])

        cmd.extend([
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-avoid_negative_ts", "make_zero", part_name,
        ])

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[FFmpeg Error Details]:\n{res.stderr}")
            raise gr.Error(f"Ошибка при нарезке видео: {res.stderr[-300:]}")

    progress(0.75, desc="Бесшовное объединение частей...")
    raw_merged = "merged_raw_gui.mp4"

    if len(temp_parts) == 1:
        if os.path.exists(raw_merged):
            os.remove(raw_merged)
        os.rename(temp_parts[0], raw_merged)
    else:
        with open("concat_gui.txt", "w", encoding="utf-8") as f:
            for p in temp_parts:
                f.write(f"file '{p}'\n")

        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", "concat_gui.txt",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                raw_merged,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

    for p in temp_parts:
        if os.path.exists(p):
            os.remove(p)
    if os.path.exists("concat_gui.txt"):
        os.remove("concat_gui.txt")

    final_target = output_path.strip().strip('"').strip("'") if output_path else "final_clip.mp4"
    if not final_target.endswith(".mp4"):
        final_target += ".mp4"
    target_dir = os.path.dirname(os.path.abspath(final_target))
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    ass_path = None
    if enable_subtitles and has_audio:
        progress(0.82, desc=f"Генерация субтитров ({WHISPER_SUBTITLES_MODEL})...")
        sub_whisper = whisper.load_model(WHISPER_SUBTITLES_MODEL)
        merged_res = sub_whisper.transcribe(
            raw_merged,
            word_timestamps=True,
            condition_on_previous_text=False,
            temperature=(0.0, 0.2),
        )
        if merged_res.get("segments"):
            ass_path = "subtitles_gui.ass"
            create_karaoke_ass(merged_res["segments"], output_ass=ass_path)

    progress(0.90, desc="Финальный рендеринг и нативная уникализация...")

    video_filters_chain = []
    audio_filters_chain = []

    if ass_path and os.path.exists(ass_path):
        escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")
        video_filters_chain.append(f"subtitles={escaped_ass}")

    if enable_uniqualize:
        u_vfilter, u_afilter = build_uniqualize_filters()
        video_filters_chain.append(u_vfilter)
        if has_audio:
            audio_filters_chain.append(u_afilter)

    video_filters_chain.append("format=yuv420p")

    final_cmd = ["ffmpeg", "-y", "-i", raw_merged]

    if video_filters_chain:
        final_cmd.extend(["-vf", ",".join(video_filters_chain)])

    if has_audio:
        if audio_filters_chain:
            final_cmd.extend(["-af", ",".join(audio_filters_chain)])
        final_cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    else:
        final_cmd.extend(["-an"])

    final_cmd.extend([
        "-map_metadata", "-1",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-profile:v", "high",
        "-level", "4.2",
        "-movflags", "+faststart",
        final_target,
    ])

    subprocess.run(final_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    if ass_path and os.path.exists(ass_path):
        os.remove(ass_path)
    if os.path.exists(raw_merged):
        os.remove(raw_merged)
    if downloaded_temp and os.path.exists(video_path):
        os.remove(video_path)

    progress(1.0, desc="Готово!")
    return final_target, f"Успешно сохранен ролик ({actual_duration} сек):\n{final_target}"