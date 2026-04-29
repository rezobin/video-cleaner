import subprocess

PADDING = 0.2

def remove_silence(input_path: str, output_path: str):

    # ⚠️ IMPORTANT: pas de split audio/vidéo
    # on garde ffmpeg responsable du sync

    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_path,

        # détecte silence mais NE découpe pas physiquement
        "-af",
        f"silenceremove=start_periods=1:start_duration={PADDING}:start_threshold=-35dB",

        "-c:v", "copy",
        "-c:a", "aac",

        output_path
    ], check=True)