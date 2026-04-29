import subprocess
import json

PADDING = 0.2


# -------------------------
# 1. AUDIO EXTRACTION
# -------------------------
def extract_audio(video_path: str, audio_path: str):

    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ], check=True)


# -------------------------
# 2. SILENCE DETECTION
# -------------------------
def detect_silence_segments(audio_path: str):

    cmd = [
        "ffmpeg", "-i", audio_path,
        "-af", "silencedetect=noise=-35dB:d=0.3",
        "-f", "null", "-"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    log = result.stderr

    silences = []

    import re
    starts = re.findall(r"silence_start: ([0-9.]+)", log)
    ends = re.findall(r"silence_end: ([0-9.]+)", log)

    for s, e in zip(starts, ends):
        silences.append((float(s), float(e)))

    return silences


# -------------------------
# 3. BUILD KEEP SEGMENTS
# -------------------------
def build_segments(duration: float, silences):

    segments = []
    last = 0.0

    for s, e in silences:
        start = max(0, last)
        end = max(0, s - PADDING)

        if end > start:
            segments.append((start, end))

        last = e + PADDING

    if last < duration:
        segments.append((last, duration))

    return segments