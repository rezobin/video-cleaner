import subprocess
import re

THRESHOLD = -35  # dB
MIN_SILENCE = 0.2
PADDING = 0.2


def get_video_duration(path: str) -> float:
    result = subprocess.check_output(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path
        ]
    )
    return float(result.decode().strip())


def detect_silences(path: str):
    """
    Retourne liste de silences [(start, end)]
    """
    cmd = [
        "ffmpeg",
        "-i", path,
        "-af", f"silencedetect=noise={THRESHOLD}dB:d={MIN_SILENCE}",
        "-f", "null",
        "-"
    ]

    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

    silences = []
    start = None

    for line in proc.stderr.split("\n"):
        if "silence_start" in line:
            start = float(line.split("silence_start: ")[1])
        elif "silence_end" in line:
            end = float(line.split("silence_end: ")[1].split(" |")[0])
            silences.append((start, end))
            start = None

    return silences


def build_segments(duration, silences):
    """
    Convertit silences → segments à garder
    """
    if not silences:
        return [(0, duration)]

    segments = []
    prev_end = 0

    for start, end in silences:
        seg_start = max(prev_end, 0)
        seg_end = max(start - PADDING, seg_start)

        if seg_end > seg_start:
            segments.append((seg_start, seg_end))

        prev_end = end + PADDING

    if prev_end < duration:
        segments.append((prev_end, duration))

    return segments