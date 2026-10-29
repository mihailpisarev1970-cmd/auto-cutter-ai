import os
import subprocess
import cv2
import mediapipe as mp
import whisper
import gradio as gr
from config import TARGET_WIDTH, TARGET_HEIGHT, WHISPER_SUBTITLES_MODEL
from subtitles import create_karaoke_ass
from downloader import download_video_stream


def has_audio_stream(file_path: str) -> bool:
    """Проверяет реальное наличие аудиопотока через ffprobe."""
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        file_path,
    ]
    try:
        res = subprocess.run(probe_cmd, capture_output=True, text=True)
        return "audio" in res.stdout.strip().lower()
    except Exception:
        return False


def get_speaker_center_crop_filter(video_path: str, duration: float) -> str:
    """
    Определяет среднюю позицию лица спикера и формирует стабильный 9:16 кроп
    с жестким контролем границ матрицы (x + target_crop_w <= width).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return f"crop=ih*{TARGET_WIDTH}/{TARGET_HEIGHT}:ih:(in_w-out_w)/2:0,scale={TARGET_WIDTH}:{TARGET_HEIGHT}"

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Вычисляем ширину окна 9:16 от высоты исходного видео
    raw_crop_w = int(height * (TARGET_WIDTH / TARGET_HEIGHT))
    target_crop_w = raw_crop_w if raw_crop_w % 2 == 0 else raw_crop_w - 1

    # Если видео уже вертикальное или слишком узкое
    if target_crop_w >= width:
        cap.release()
        return (
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2"
        )

    # Максимально допустимая координата X, чтобы не выйти за правый край
    max_x = max(0, width - target_crop_w)
    default_x = float(max_x / 2.0)

    face_detection = None
    if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_detection"):
        try:
            face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.40
            )
        except Exception:
            face_detection = None

    detected_centers = []
    step = max(1, int(fps))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or int(duration * fps)

    for f_idx in range(0, total_frames, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        if not ret:
            break

        if face_detection is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb)
            if results.detections:
                best_face = max(
                    results.detections,
                    key=lambda d: d.location_data.relative_bounding_box.width * d.location_data.relative_bounding_box.height
                )
                bbox = best_face.location_data.relative_bounding_box
                face_center_x = (bbox.xmin + bbox.width / 2.0) * width
                desired_x = face_center_x - (target_crop_w / 2.0)
                desired_x = max(0.0, min(float(desired_x), float(max_x)))
                detected_centers.append(desired_x)

    cap.release()
    if face_detection is not None:
        face_detection.close()

    if detected_centers:
        detected_centers.sort()
        chosen_x = int(detected_centers[len(detected_centers) // 2])
    else:
        chosen_x = int(default_x)

    # Принудительная четность и защита от вылета за границы
    if chosen_x % 2 != 0:
        chosen_x -= 1
    safe_x = max(0, min(chosen_x, max_x))

    return f"crop={target_crop_w}:{height}:{safe_x}:0,scale={TARGET_WIDTH}:{TARGET_HEIGHT}"


def convert_16_9_to_9_16(
    url_source: str,
    local_file,
    output_path: str,
    crop_mode: str,
    enable_subtitles: bool,
    progress=gr.Progress(),
):
    progress(0.05, desc="Подготовка видео...")
    video_path = ""
    downloaded_temp = False

    if url_source and url_source.strip().startswith(("http://", "https://")):
        video_path = "temp_convert_src.mp4"
        download_video_stream(url_source, video_path)
        downloaded_temp = True
    elif local_file is not None:
        video_path = local_file if isinstance(local_file, str) else local_file.name
    else:
        raise gr.Error("Укажите ссылку или загрузите видеофайл!")

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = (frame_count / fps) if frame_count > 0 else 0.0
    cap.release()

    progress(0.25, desc="Кадрирование в 9:16...")
    temp_target = "temp_converted_no_sub.mp4"
    has_audio = has_audio_stream(video_path)

    cmd = ["ffmpeg", "-y", "-i", video_path]

    if crop_mode == "full":
        cmd.extend([
            "-vf", f"scale=-2:{TARGET_HEIGHT},crop={TARGET_WIDTH}:{TARGET_HEIGHT}:(in_w-{TARGET_WIDTH})/2:0,format=yuv420p",
            "-map", "0:v:0"
        ])
    elif crop_mode == "autotrack":
        v_filter = get_speaker_center_crop_filter(video_path, duration)
        cmd.extend([
            "-vf", f"{v_filter},format=yuv420p",
            "-map", "0:v:0"
        ])
    else:
        filter_blur = (
            f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},boxblur=20:2[bg];"
            f"[0:v]scale={TARGET_WIDTH}:-2[fg];"
            f"[bg][fg]overlay=0:(H-h)/2,format=yuv420p[outv]"
        )
        cmd.extend([
            "-filter_complex", filter_blur,
            "-map", "[outv]"
        ])

    if has_audio:
        cmd.extend(["-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k"])
    else:
        cmd.extend(["-an"])

    cmd.extend([
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        temp_target
    ])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        error_lines = [l for l in res.stderr.splitlines() if "error" in l.lower() or "invalid" in l.lower()]
        summary = "\n".join(error_lines[-5:]) if error_lines else res.stderr[-350:]
        raise gr.Error(f"Ошибка FFmpeg при кадрировании:\n{summary}")

    final_target = output_path.strip().strip('"').strip("'") if output_path else "converted_9_16.mp4"
    if not final_target.endswith(".mp4"):
        final_target += ".mp4"
    target_dir = os.path.dirname(os.path.abspath(final_target))
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    if enable_subtitles and has_audio:
        progress(0.70, desc=f"Создание караоке-субтитров (Whisper {WHISPER_SUBTITLES_MODEL})...")
        sub_whisper = whisper.load_model(WHISPER_SUBTITLES_MODEL)
        res_whisper = sub_whisper.transcribe(
            temp_target,
            language="ru",
            word_timestamps=True,
            condition_on_previous_text=False,
            no_speech_threshold=0.85,
            temperature=(0.0, 0.2),
        )
        ass_path = "subtitles_conv.ass"
        create_karaoke_ass(res_whisper["segments"], output_ass=ass_path)
        escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")

        sub_cmd = [
            "ffmpeg", "-y", "-i", temp_target,
            "-vf", f"subtitles={escaped_ass},format=yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "copy",
            final_target,
        ]
        sub_res = subprocess.run(sub_cmd, capture_output=True, text=True)
        if sub_res.returncode != 0:
            if os.path.exists(ass_path):
                os.remove(ass_path)
            raise gr.Error(f"Ошибка FFmpeg при наложении субтитров:\n{sub_res.stderr[-300:]}")

        if os.path.exists(ass_path):
            os.remove(ass_path)
        if os.path.exists(temp_target):
            os.remove(temp_target)
    else:
        if os.path.exists(final_target):
            os.remove(final_target)
        os.rename(temp_target, final_target)

    if downloaded_temp and os.path.exists(video_path):
        os.remove(video_path)

    progress(1.0, desc="Готово!")
    return final_target, f"Успешно сохранено в 9:16:\n{final_target}"