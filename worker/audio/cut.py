import subprocess
import re

PADDING = 0.2


def extract_audio(input_path, audio_path):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_path,
        "-vn",
        "-acodec", "pcm_s16le",
        audio_path
    ], check=True)


def detect_silence_segments(audio_path):
    """
    Retourne les segments audio NON silencieux
    via ffmpeg silencedetect
    """

    cmd = [
        "ffmpeg", "-i", audio_path,
        "-af", "silencedetect=noise=-35dB:d=0.3",
        "-f", "null", "-"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    lines = result.stderr.split("\n")

    silences = []
    for line in lines:
        if "silence_start" in line:
            t = float(line.split("silence_start:")[1])
            silences.append(("start", t))
        if "silence_end" in line:
            parts = line.split("silence_end:")[1].split("|")
            t = float(parts[0])
            silences.append(("end", t))

    return silences


def build_segments(duration, silences):
    """
    Convertit silences → segments actifs
    + padding 0.2s
    """

    segments = []

    last_end = 0.0

    for i in range(0, len(silences), 2):
        if i + 1 >= len(silences):
            break

        silence_start = silences[i][1]
        silence_end = silences[i + 1][1]

        start = max(0, last_end - PADDING)
        end = max(0, silence_start + PADDING)

        if end > start:
            segments.append((start, end))

        last_end = silence_end

    # dernier segment
    segments.append((last_end, duration))

    return segments