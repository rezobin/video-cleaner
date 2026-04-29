import subprocess

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
    cmd = [
        "ffmpeg",
        "-i", path,
        "-af", f"silencedetect=noise={THRESHOLD}dB:d={MIN_SILENCE}",
        "-f", "null",
        "-"
    ]

    print("[FFMPEG DETECT]", " ".join(cmd))

    proc = subprocess.run(
        cmd,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60
    )

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
    if not silences:
        return [(0, duration)]

    segments = []
    prev_end = 0

    for start, end in silences:

        seg_start = max(prev_end, 0)
        seg_end = max(start - PADDING, seg_start)

        # 🔴 évite segments trop courts (cause #1 des freezes)
        if seg_end - seg_start > 0.3:
            segments.append((seg_start, seg_end))

        prev_end = end + PADDING

    if duration - prev_end > 0.3:
        segments.append((prev_end, duration))

    return segments