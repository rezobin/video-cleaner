import subprocess

THRESHOLD = "-38dB"
MIN_SILENCE = 0.25
PADDING = 0.12
MIN_SEGMENT = 0.5


def detect_silences_ffmpeg(input_path: str):

    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-af", f"silencedetect=noise={THRESHOLD}:d={MIN_SILENCE}",
        "-f", "null",
        "-"
    ]

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

    silences = []

    start = None

    for line in result.stderr.split("\n"):

        if "silence_start" in line:
            try:
                start = float(line.split("silence_start: ")[1])
            except:
                pass

        if "silence_end" in line and start is not None:
            try:
                end = float(line.split("silence_end: ")[1].split(" ")[0])
                silences.append((start, end))
                start = None
            except:
                pass

    return silences


def build_segments(duration, silences):

    segments = []
    cursor = 0.0

    for start, end in silences:

        start = max(0, start - PADDING)
        end = min(duration, end + PADDING)

        if start > cursor:
            segments.append((cursor, start))

        cursor = end

    if cursor < duration:
        segments.append((cursor, duration))

    return [
        (s, e) for s, e in segments
        if (e - s) >= MIN_SEGMENT
    ]