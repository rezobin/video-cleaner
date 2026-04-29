import subprocess

def remove_silence(input_path: str, output_path: str):

    """
    Silence removal simple + stable
    (version MVP scalable)
    """

    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_path,
        "-af",
        # silence detection + keep small padding logic
        "silenceremove=start_periods=1:start_duration=0.2:start_threshold=-35dB",
        output_path
    ], check=True)