import subprocess

THRESHOLD = "-32dB"
MIN_SILENCE = 0.25
PADDING = 0.08
MIN_SEGMENT = 0.5


def detect_silences(video_path):
    print("[DETECT START]", flush=True)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i", video_path,

        "-vn",  # 🔥 ignore video → MASSIVE speed gain
        "-af", f"silencedetect=noise={THRESHOLD}:d={MIN_SILENCE}",
        "-f", "null",
        "-"
    ]

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

    print("[DETECT DONE]", flush=True)

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


def align(t, fps=30):
    return round(t * fps) / fps

def build_segments(duration, silences):
    segments = []
    cursor = 0.0

    for start, end in silences:
        
        start = align(start - PADDING)
        end = align(end + PADDING)

        if start > cursor:
            segments.append((cursor, start))

        cursor = end

    if cursor < duration:
        segments.append((cursor, duration))

    segments = [(s, e) for s, e in segments if (e - s) >= MIN_SEGMENT]

    print(f"[SEGMENTS BUILT] {len(segments)}", flush=True)

    return segments