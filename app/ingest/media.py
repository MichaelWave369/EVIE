from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import tempfile, subprocess

from app.settings import settings

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}

def extract_text_from_image(path: Path) -> str:
    backend = (settings.ocr_backend or "none").lower().strip()
    if backend == "none":
        return ""
    if backend != "tesseract":
        raise ValueError(f"Unknown EV_OCR_BACKEND: {settings.ocr_backend}")

    try:
        from PIL import Image
        import pytesseract
    except Exception as e:
        raise RuntimeError("OCR requested but Pillow/pytesseract not installed. pip install pillow pytesseract") from e

    # pytesseract relies on a system tesseract installation
    img = Image.open(str(path))
    return (pytesseract.image_to_string(img) or "").strip()

def _extract_audio_with_ffmpeg(src: Path) -> Path:
    # Convert any audio/video to 16k mono wav for best whisper results.
    tmpdir = Path(tempfile.mkdtemp(prefix="embervault_media_"))
    out = tmpdir / "audio.wav"
    cmd = [
        settings.ffmpeg_bin,
        "-y",
        "-i", str(src),
        "-ac", "1",
        "-ar", "16000",
        str(out),
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({p.returncode}): {p.stderr.decode('utf-8', errors='ignore')[:500]}")
    return out

def transcribe_media(path: Path) -> str:
    backend = (settings.transcribe_backend or "none").lower().strip()
    if backend == "none":
        return ""

    wav = path
    if path.suffix.lower() in VIDEO_EXTS or path.suffix.lower() in AUDIO_EXTS:
        # Whisper prefers wav; for wav we can keep it as-is.
        if path.suffix.lower() != ".wav":
            wav = _extract_audio_with_ffmpeg(path)

    if backend == "faster_whisper":
        try:
            from faster_whisper import WhisperModel
        except Exception as e:
            raise RuntimeError("EV_TRANSCRIBE_BACKEND=faster_whisper but faster-whisper not installed. pip install faster-whisper") from e
        model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(wav))
        text_parts = [seg.text for seg in segments]
        return (" ".join(text_parts)).strip()

    if backend == "whisper":
        try:
            import whisper
        except Exception as e:
            raise RuntimeError("EV_TRANSCRIBE_BACKEND=whisper but openai-whisper not installed. pip install openai-whisper") from e
        model = whisper.load_model(settings.whisper_model)
        result = model.transcribe(str(wav))
        return (result.get("text") or "").strip()

    raise ValueError(f"Unknown EV_TRANSCRIBE_BACKEND: {settings.transcribe_backend}")
