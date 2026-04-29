import subprocess

# paramètres ajustables
THRESHOLD = "-35dB"
MIN_SILENCE = "0.2"
PADDING = "0.2"

def remove_silence(input_path: str, output_path: str):
    """
    Coupe les silences en gardant sync audio/video
    """

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,

        "-af",
        f"silenceremove="
        f"start_periods=1:"
        f"start_duration={MIN_SILENCE}:"
        f"start_threshold={THRESHOLD}:"
        f"stop_periods=-1:"
        f"stop_duration={MIN_SILENCE}:"
        f"stop_threshold={THRESHOLD}",

        # 🔴 IMPORTANT QUALITÉ
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",

        "-c:a", "aac",
        "-b:a", "192k",

        "-movflags", "+faststart",

        output_path
    ]

    subprocess.run(cmd, check=True)