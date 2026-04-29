import subprocess

THRESHOLD = -40
MIN_SILENCE = 0.5
PADDING = 0.3


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
    print(f"[DEBUG] silences: {silences}")

    start = None

    for line in proc.stderr.split("\n"):
        if "silence_start" in line:
            start = float(line.split("silence_start: ")[1])
        elif "silence_end" in line:
            end = float(line.split("silence_end: ")[1].split(" |")[0])
            silences.append((start, end))
            start = None

    return silences


def build_segments(duration, silences, padding=0.3):

    segments = []
    last_end = 0.0

    for silence_start, silence_end in silences:

        seg_start = last_end
        seg_end = silence_start

        # ajoute padding
        seg_start = max(0, seg_start - padding)
        seg_end = min(duration, seg_end + padding)

        if seg_end - seg_start > 0.8:  # 🔴 important
            segments.append((seg_start, seg_end))

        last_end = silence_end

    # dernier segment après le dernier silence
    if last_end < duration:
        seg_start = max(0, last_end - padding)
        seg_end = duration

        if seg_end - seg_start > 0.8:
            segments.append((seg_start, seg_end))

    print(f"[DEBUG] segments: {segments}")

    return segments