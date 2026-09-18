from __future__ import annotations
from pathlib import Path
from typing import Tuple
from pypdf import PdfReader

from app.ingest.media import IMAGE_EXTS, AUDIO_EXTS, VIDEO_EXTS, extract_text_from_image, transcribe_media

def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t.strip():
            parts.append(t)
    return "\n\n".join(parts).strip()

def extract_text_from_file(path: Path) -> Tuple[str, str]:
    """
    Returns (kind, text) for local-only ingestion.

    Supported:
      - .txt/.md
      - .pdf (text layer)
      - images (optional OCR)
      - audio/video (optional local whisper transcription)
    """
    suffix = path.suffix.lower()

    if suffix in [".txt", ".md", ".markdown"]:
        return ("text", path.read_text(encoding="utf-8", errors="ignore"))

    if suffix == ".pdf":
        return ("pdf", extract_text_from_pdf(path))

    if suffix in IMAGE_EXTS:
        text = extract_text_from_image(path)
        return ("image", text)

    if suffix in AUDIO_EXTS or suffix in VIDEO_EXTS:
        text = transcribe_media(path)
        return ("media", text)

    # default: best-effort decode
    return ("binary", path.read_text(encoding="utf-8", errors="ignore"))
