from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def convert_to_mp3(input_path: Path, output_path: Optional[Path] = None, bitrate: int = 320) -> Path:
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_suffix(".mp3")

    output_path = Path(output_path)

    if input_path.suffix.lower() == ".mp3" and input_path == output_path:
        return input_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-codec:a", "libmp3lame",
        "-b:a", f"{bitrate}k",
        "-map_metadata", "0",
        "-id3v2_version", "3",
        "-y",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    return output_path


def needs_conversion(filepath: Path, target_format: str = "mp3") -> bool:
    return filepath.suffix.lower() != f".{target_format}"


def get_audio_duration(filepath: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(filepath),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError):
        return 0.0
