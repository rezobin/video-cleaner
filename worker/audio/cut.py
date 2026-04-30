import subprocess

THRESHOLD = "-38dB"
MIN_SILENCE = 0.25
PADDING = 0.15
MIN_SEGMENT = 0.6


def detect_silences(video_path):
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i", video_path,
        "-af", f"silencedetect=noise={THRESHOLD}:d={MIN_SILENCE}",
        "-f", "null",
        "-"
    ]

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

    starts = []
    ends = []

    for line in result.stderr.split("\n"):
        if "silence_start" in line:
            try:
                starts.append(float(line.split("silence_start: ")[1]))
            except:
                pass

        if "silence_end" in line:
            try:
                ends.append(float(line.split("silence_end: ")[1].split(" ")[0]))
            except:
                pass

    return list(zip(starts, ends))


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

    return [(s, e) for s, e in segments if (e - s) >= MIN_SEGMENT]