from config import TARGET_WIDTH, TARGET_HEIGHT, SUBTITLE_FONT_SIZE, SUBTITLE_MARGIN_V

def format_ass_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

def create_karaoke_ass(segments, output_ass="subtitles.ass"):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {TARGET_WIDTH}
PlayResY: {TARGET_HEIGHT}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{SUBTITLE_FONT_SIZE},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,0,2,40,40,{SUBTITLE_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for seg in segments:
        words = seg.get("words", [])
        if not words:
            continue

        chunk_size = 4
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            if not chunk:
                continue

            line_start = chunk[0]["start"]
            line_end = chunk[-1]["end"]

            if line_end <= line_start:
                line_end = line_start + 0.5

            start_str = format_ass_time(line_start)
            end_str = format_ass_time(line_end)

            karaoke_text = ""
            for w in chunk:
                w_start = w.get("start", line_start)
                w_end = w.get("end", line_end)
                duration_cs = max(1, int(round((w_end - w_start) * 100)))
                clean_w = w.get("word", "").strip()
                if clean_w:
                    karaoke_text += f"{{\\k{duration_cs}}}{clean_w} "

            if karaoke_text.strip():
                events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{karaoke_text.strip()}")

    with open(output_ass, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))