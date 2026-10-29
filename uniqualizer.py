import os
import random
import subprocess
import sys
from pathlib import Path


def process_video(
    input_file: Path,
    output_file: Path,
    target_width: int = 1080,
    target_height: int = 1920,
) -> bool:
    """Обрабатывает одно видео: уникализирует параметры без потери качества."""
    print(f"\n[+] Обработка: {input_file.name}")

    # 1. Генерируем случайные микро-изменения для уникализации
    # Скорость от 1.02 до 1.04 (+2-4% незаметно для уха и глаза)
    speed = round(random.uniform(1.02, 1.04), 3)
    pts = round(1.0 / speed, 4)

    # Небольшой зум/кроп (срезаем от 3% до 5% по краям)
    crop_factor = round(random.uniform(0.95, 0.97), 3)

    # Микро-коррекция цвета
    contrast = round(random.uniform(1.01, 1.03), 2)
    brightness = round(random.uniform(0.005, 0.015), 3)
    saturation = round(random.uniform(1.02, 1.05), 2)

    # Уровень шума: минимальный (2-3), чтобы не портить картинку
    noise_level = random.randint(2, 3)

    # Незначительный сдвиг частоты дискретизации аудио (Pitch Shift без искажений)
    sample_rate_shift = round(random.uniform(1.008, 1.015), 3)

    # 2. Формируем цепочку видеофильтров
    # - crop: сдвиг пикселей
    # - scale: масштабирование через алгоритм lanczos (сохраняет четкость)
    # - unsharp: компенсация потерь резкости после зума
    # - eq: изменение цветового профиля
    # - noise: микро-зерно против цифровых отпечатков кадра
    # - setpts: синхронизация видеоряда со звуком
    video_filters = (
        f"crop=in_w*{crop_factor}:in_h*{crop_factor},"
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={target_width}:{target_height},"
        f"unsharp=3:3:0.6:3:3:0.0,"
        f"eq=contrast={contrast}:brightness={brightness}:saturation={saturation},"
        f"noise=alls={noise_level}:allf=t+u,"
        f"setpts={pts}*PTS"
    )

    # 3. Аудиофильтры: изменение темпа и тональности
    audio_filters = (
        f"atempo={speed},"
        f"asetrate=44100*{sample_rate_shift},"
        f"aresample=44100"
    )

    # 4. Команда сборки FFmpeg
    cmd = [
        "ffmpeg",
        "-y",  # перезаписывать существующий файл
        "-i",
        str(input_file),
        "-vf",
        video_filters,
        "-af",
        audio_filters,
        "-map_metadata",
        "-1",  # полная очистка метаданных
        "-c:v",
        "libx264",
        "-crf",
        "18",  # визуально без потерь (visually lossless)
        "-preset",
        "slow",  # качественная упаковка кадров
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-pix_fmt",
        "yuv420p",  # стандарт для максимальной совместимости с мобильными плеерами ВК
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",  # оптимизация для мгновенного старта воспроизведения в сети
        str(output_file),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"[✓] Успешно сохранено: {output_file.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Ошибка при обработке {input_file.name}:")
        print(e.stderr.decode("utf-8", errors="ignore"))
        return False


def batch_uniqualize(input_dir: str = "input", output_dir: str = "output"):
    """Сканирует папку input и сохраняет уникализированные ролики в output."""
    in_path = Path(input_dir)
    out_path = Path(output_dir)

    out_path.mkdir(parents=True, exist_ok=True)

    supported_extensions = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
    video_files = [f for f in in_path.iterdir() if f.suffix.lower() in supported_extensions]

    if not video_files:
        print(f"[!] В папке '{input_dir}' не найдено поддерживаемых видеофайлов.")
        return

    print(f"[*] Найдено файлов для обработки: {len(video_files)}")

    success_count = 0
    for video in video_files:
        out_file = out_path / f"unique_{video.stem}.mp4"
        if process_video(video, out_file):
            success_count += 1

    print(f"\n[=] Готово! Успешно обработано: {success_count}/{len(video_files)}")


if __name__ == "__main__":
    # Проверяем наличие установленного ffmpeg в системе
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("[КРИТИЧЕСКАЯ ОШИБКА] Утилита ffmpeg не найдена в системе!")
        print("Убедитесь, что FFmpeg установлен и добавлен в системную переменную PATH.")
        sys.exit(1)

    # Создаем папки по умолчанию, если их нет
    os.makedirs("input", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    print("=== Уникализатор клипов без потери качества ===")
    print("Положите исходные видео в папку 'input' и нажмите Enter.")
    input("Нажмите Enter для старта...")

    batch_uniqualize(input_dir="input", output_dir="output")