"""Extract key frames from video files using ffmpeg."""
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_frames(video_path: str, interval_seconds: int = 5, max_frames: int = 20) -> list[Path]:
    """Extract key frames from a video at regular intervals.

    Returns list of paths to JPEG frame images (in a temp directory).
    Caller is responsible for cleanup.
    """
    path = Path(video_path)
    if not path.exists():
        logger.warning("Video not found: %s", video_path)
        return []

    # Get video duration
    duration = _get_duration(video_path)
    if duration is None or duration <= 0:
        logger.warning("Could not determine video duration")
        return []

    # Calculate interval to stay within max_frames
    total_possible = int(duration / interval_seconds)
    if total_possible > max_frames:
        interval_seconds = int(duration / max_frames)

    # Create temp directory for frames
    tmpdir = Path(tempfile.mkdtemp(prefix="frames_"))

    try:
        cmd = [
            "ffmpeg", "-i", str(path),
            "-vf", f"fps=1/{interval_seconds}",
            "-q:v", "2",
            "-frames:v", str(max_frames),
            str(tmpdir / "frame_%04d.jpg"),
            "-y", "-loglevel", "warning"
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error("ffmpeg frame extraction failed: %s", e.stderr.decode())
        return []

    frames = sorted(tmpdir.glob("frame_*.jpg"))
    logger.info("Extracted %d frames from %s (%.0fs video, every %ds)",
                len(frames), path.name, duration, interval_seconds)
    return frames


def _get_duration(video_path: str) -> float | None:
    """Get video duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception:
        logger.warning("Could not get video duration")
        return None
