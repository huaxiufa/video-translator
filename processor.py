import os
import re
import subprocess
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator

MODEL_SIZE = os.getenv("WHISPER_MODEL", "tiny.en")
MODEL_DIR = Path(os.getenv("WHISPER_MODEL_DIR", "/opt/render/project/src/models"))
MODEL_DIR.mkdir(parents=True, exist_ok=True)

_model = None
_translator = None


def get_model():
    global _model
    if _model is None:
        # If the model was downloaded during Render's build step, this uses it.
        # Otherwise faster-whisper will download it automatically.
        _model = WhisperModel(
            MODEL_SIZE,
            device=os.getenv("WHISPER_DEVICE", "cpu"),
            compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
            download_root=str(MODEL_DIR),
        )
    return _model


def get_translator():
    global _translator
    if _translator is None:
        _translator = GoogleTranslator(source="en", target="zh-CN")
    return _translator


def run_cmd(cmd):
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "命令执行失败:\n"
            + " ".join(map(str, cmd))
            + "\n"
            + result.stderr[-4000:]
        )
    return result.stdout


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def srt_time(seconds):
    ms = max(0, int(round(seconds * 1000)))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def ass_time(seconds):
    cs = max(0, int(round(seconds * 100)))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def ass_escape(text):
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def write_srt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{srt_time(seg['start'])} --> {srt_time(seg['end'])}\n")
            f.write(seg["english"] + "\n")
            f.write(seg["chinese"] + "\n\n")


def write_ass(segments, path):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: EN,Noto Sans,42,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,70,70,115,1
Style: ZH,Noto Sans CJK SC,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,8,70,70,115,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        for seg in segments:
            f.write(
                f"Dialogue: 0,{ass_time(seg['start'])},{ass_time(seg['end'])},EN,,0,0,0,,"
                f"{ass_escape(seg['english'])}\n"
            )
            f.write(
                f"Dialogue: 0,{ass_time(seg['start'])},{ass_time(seg['end'])},ZH,,0,0,0,,"
                f"{ass_escape(seg['chinese'])}\n"
            )


def translate_text(text):
    text = clean_text(text)
    if not text:
        return ""
    translator = get_translator()
    # Google Translate web endpoint can reject very large chunks, so keep
    # individual subtitle translations reasonably small.
    if len(text) <= 4500:
        return translator.translate(text)

    pieces = re.split(r"(?<=[.!?])\s+", text)
    out = []
    current = ""
    for piece in pieces:
        if len(current) + len(piece) + 1 <= 4000:
            current = (current + " " + piece).strip()
        else:
            if current:
                out.append(translator.translate(current))
            current = piece
    if current:
        out.append(translator.translate(current))
    return " ".join(out)


def process_video(input_path, output_dir, progress):
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    job_id = input_path.stem

    progress(5, "加载 Whisper 模型…")
    model = get_model()

    progress(15, "识别英文语音…")
    segments_iter, info = model.transcribe(
        str(input_path),
        beam_size=1,
        language="en",
        vad_filter=True,
        condition_on_previous_text=True,
    )

    segments = []
    raw = list(segments_iter)
    total = max(len(raw), 1)

    for i, seg in enumerate(raw, 1):
        english = clean_text(seg.text)
        if not english:
            continue
        progress(15 + int(40 * i / total), f"翻译字幕 {i}/{total}…")
        chinese = translate_text(english)
        segments.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "english": english,
            "chinese": chinese,
        })

    if not segments:
        raise RuntimeError("没有识别到英文语音。")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        srt_path = td / "bilingual.srt"
        ass_path = td / "bilingual.ass"
        write_srt(segments, srt_path)
        write_ass(segments, ass_path)

        progress(65, "生成双语字幕…")
        output_path = output_dir / f"{job_id}.mp4"

        # Use ASS to place English at the bottom and Chinese above it.
        # libass is included in standard Ubuntu/Render ffmpeg packages.
        subtitle_filter = f"subtitles={ass_path.as_posix()}"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", os.getenv("FFMPEG_PRESET", "veryfast"),
            "-crf", os.getenv("FFMPEG_CRF", "23"),
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_path),
        ]
        progress(70, "烧录双语字幕到视频…")
        run_cmd(cmd)

    progress(98, "整理输出文件…")
    return output_path
