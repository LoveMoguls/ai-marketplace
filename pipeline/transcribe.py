"""Transcribe MP4 pitch videos using OpenAI Whisper."""
import logging
from pathlib import Path

import whisper

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        logger.info("Loading Whisper model (base)...")
        _model = whisper.load_model("base")
    return _model


def transcribe(mp4_path: str) -> str | None:
    """Transcribe an MP4 file to text using Whisper.

    Returns transcript string, or None if file not found.
    """
    path = Path(mp4_path)
    if not path.exists():
        logger.warning("MP4 not found: %s", mp4_path)
        return None

    logger.info("Transcribing %s ...", path.name)
    model = _get_model()
    result = model.transcribe(str(path))
    transcript = result["text"].strip()
    logger.info("Transcription complete: %d chars", len(transcript))
    return transcript
