"""
Media processing for AlpieCode — video frame extraction & YouTube download.

Supports:
  - Video files: .mp4, .avi, .mov, .mkv, .webm → extract key frames via ffmpeg
  - YouTube URLs: download via yt-dlp → extract frames
  - Images: pass-through (already supported in agent.py)

Uses ffmpeg for frame extraction (no heavy Python deps like opencv).
"""

import base64
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from rich.console import Console
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    class _Fallback:
        def print(self, *a, **kw):
            kw.pop("style", None)
            kw.pop("highlight", None)
            print(*a, **kw)
    console = _Fallback()


# ── Constants ─────────────────────────────────────────────────────────

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
MAX_FRAMES = 8  # Max frames to extract from a video (balances context vs quality)
FRAME_QUALITY = 85  # JPEG quality for extracted frames


# ── YouTube URL detection ─────────────────────────────────────────────

YOUTUBE_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
    r"(?:https?://)?youtu\.be/[\w-]+",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
]


def is_youtube_url(url: str) -> bool:
    """Check if a string is a YouTube URL."""
    return any(re.match(pattern, url) for pattern in YOUTUBE_PATTERNS)


def is_video_file(path: str) -> bool:
    """Check if a file path is a supported video format."""
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def is_image_file(path: str) -> bool:
    """Check if a file path is a supported image format."""
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


# ── Frame extraction via ffmpeg ───────────────────────────────────────

def _get_video_duration(video_path: str) -> Optional[float]:
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def extract_frames(video_path: str, max_frames: int = MAX_FRAMES) -> List[Tuple[str, bytes]]:
    """
    Extract key frames from a video using ffmpeg.

    Returns:
        List of (mime_type, raw_bytes) tuples for each extracted frame.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg is required for video processing. "
            "Install it with: sudo apt install ffmpeg"
        )

    video_path = str(Path(video_path).resolve())
    duration = _get_video_duration(video_path)

    with tempfile.TemporaryDirectory(prefix="alpiecode_frames_") as tmpdir:
        if duration and duration > 0:
            # Extract evenly-spaced frames across the video duration
            interval = duration / (max_frames + 1)
            frames = []
            for i in range(1, max_frames + 1):
                timestamp = interval * i
                out_path = os.path.join(tmpdir, f"frame_{i:03d}.jpg")
                subprocess.run(
                    ["ffmpeg", "-ss", f"{timestamp:.2f}", "-i", video_path,
                     "-vframes", "1", "-q:v", str(FRAME_QUALITY // 10),
                     "-y", out_path],
                    capture_output=True, timeout=30,
                )
                if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    frames.append(("image/jpeg", Path(out_path).read_bytes()))
            return frames if frames else _extract_frames_fallback(video_path, tmpdir, max_frames)
        else:
            return _extract_frames_fallback(video_path, tmpdir, max_frames)


def _extract_frames_fallback(video_path: str, tmpdir: str, max_frames: int) -> List[Tuple[str, bytes]]:
    """Fallback: extract frames at 1 fps and pick evenly-spaced ones."""
    subprocess.run(
        ["ffmpeg", "-i", video_path, "-vf", "fps=1", "-q:v", "2",
         "-y", os.path.join(tmpdir, "frame_%04d.jpg")],
        capture_output=True, timeout=120,
    )
    all_frames = sorted(Path(tmpdir).glob("frame_*.jpg"))
    if not all_frames:
        raise RuntimeError(f"ffmpeg failed to extract any frames from {video_path}")

    # Pick evenly spaced frames
    step = max(1, len(all_frames) // max_frames)
    selected = all_frames[::step][:max_frames]
    return [("image/jpeg", f.read_bytes()) for f in selected]


# ── YouTube download via yt-dlp ───────────────────────────────────────

def download_youtube(url: str, output_dir: str = None) -> str:
    """
    Download a YouTube video using yt-dlp.

    Returns:
        Path to the downloaded video file.
    """
    if not shutil.which("yt-dlp"):
        raise RuntimeError(
            "yt-dlp is required for YouTube downloads. "
            "Install it with: uv pip install yt-dlp"
        )

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="alpiecode_yt_")

    output_template = os.path.join(output_dir, "video.%(ext)s")

    result = subprocess.run(
        ["yt-dlp",
         "-f", "best[height<=720]",  # Cap at 720p to keep frames reasonable
         "--no-playlist",
         "-o", output_template,
         url],
        capture_output=True, text=True, timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr[:500]}")

    # Find the downloaded file
    for f in Path(output_dir).iterdir():
        if f.suffix.lower() in VIDEO_EXTENSIONS and f.stat().st_size > 0:
            return str(f)

    raise RuntimeError(f"yt-dlp download completed but no video file found in {output_dir}")


# ── High-level: build multimodal content ──────────────────────────────

def build_media_content(
    task: str,
    image_path: Optional[str] = None,
    video_path: Optional[str] = None,
    url: Optional[str] = None,
    workdir: Path = None,
) -> list:
    """
    Build a multimodal message content array from text + optional media.

    Handles:
      - image_path: single image → 1 image_url entry
      - video_path: video file → N frame image_url entries
      - url: YouTube URL → download + extract frames

    Returns:
        list suitable for OpenAI messages[].content (text + image_url entries)
    """
    content = [{"type": "text", "text": task}]
    workdir = workdir or Path(".")

    # ── Image ──
    if image_path:
        img_file = workdir / image_path if not Path(image_path).is_absolute() else Path(image_path)
        if img_file.exists():
            ext = img_file.suffix.lower().lstrip(".")
            mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
            b64 = base64.b64encode(img_file.read_bytes()).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })
            if HAS_RICH:
                console.print(f"🖼️  Image loaded: {image_path}", style="cyan")
        else:
            if HAS_RICH:
                console.print(f"⚠️  Image not found: {image_path}", style="yellow")

    # ── Video file ──
    if video_path:
        vid_file = workdir / video_path if not Path(video_path).is_absolute() else Path(video_path)
        if vid_file.exists():
            if HAS_RICH:
                console.print(f"🎬 Extracting frames from: {video_path}...", style="cyan")
            try:
                frames = extract_frames(str(vid_file))
                for i, (mime, raw_bytes) in enumerate(frames):
                    b64 = base64.b64encode(raw_bytes).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    })
                if HAS_RICH:
                    console.print(f"   ✅ Extracted {len(frames)} frames", style="green")
            except RuntimeError as e:
                if HAS_RICH:
                    console.print(f"   ❌ {e}", style="red")
        else:
            if HAS_RICH:
                console.print(f"⚠️  Video not found: {video_path}", style="yellow")

    # ── YouTube URL ──
    if url and is_youtube_url(url):
        if HAS_RICH:
            console.print(f"📺 Downloading YouTube video: {url}...", style="cyan")
        try:
            downloaded = download_youtube(url)
            if HAS_RICH:
                console.print(f"   ✅ Downloaded: {Path(downloaded).name}", style="green")
                console.print(f"🎬 Extracting frames...", style="cyan")
            frames = extract_frames(downloaded)
            for mime, raw_bytes in frames:
                b64 = base64.b64encode(raw_bytes).decode("utf-8")
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                })
            if HAS_RICH:
                console.print(f"   ✅ Extracted {len(frames)} frames from YouTube video", style="green")
            # Clean up downloaded video
            try:
                os.remove(downloaded)
                os.rmdir(str(Path(downloaded).parent))
            except OSError:
                pass
        except RuntimeError as e:
            if HAS_RICH:
                console.print(f"   ❌ {e}", style="red")

    # If only text was added, return the plain string (no media)
    if len(content) == 1:
        return task

    return content
