import subprocess

THRESHOLD = "-40dB"
MIN_SILENCE = 0.25
PADDING = 0.15
MIN_SEGMENT = 0.6


def extract_audio(input_path, output_path):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        output_path
    ], check=True)


def detect_silences(audio_path):

    cmd = [
        "ffmpeg",
        "-i", audio_path,
        "-af", f"silencedetect=noise={THRESHOLD}:d={MIN_SILENCE}",
        "-f", "null",
        "-"
    ]

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

    silence_starts = []
    silence_ends = []

    for line in result.stderr.split("\n"):
        if "silence_start" in line:
            silence_starts.append(float(line.split("silence_start: ")[1]))
        elif "silence_end" in line:
            silence_ends.append(float(line.split("silence_end: ")[1].split(" ")[0]))

    return list(zip(silence_starts, silence_ends))


def build_segments(duration, silences):

    segments = []
    current = 0.0

    for start, end in silences:

        start = max(0, start - PADDING)
        end = min(duration, end + PADDING)

        if start > current:
            segments.append((current, start))

        current = end

    if current < duration:
        segments.append((current, duration))

    # 🔴 filtre segments trop courts
    filtered = []
    for s, e in segments:
        if e - s >= MIN_SEGMENT:
            filtered.append((s, e))

    return filtered