import os
from pathlib import Path
from faster_whisper import WhisperModel

model_size = os.getenv("WHISPER_MODEL", "tiny.en")
model_dir = Path(os.getenv("WHISPER_MODEL_DIR", "/opt/render/project/src/models"))
model_dir.mkdir(parents=True, exist_ok=True)

print(f"Downloading/preparing Whisper model: {model_size}")
WhisperModel(
    model_size,
    device="cpu",
    compute_type="int8",
    download_root=str(model_dir),
)
print("Whisper model ready.")
