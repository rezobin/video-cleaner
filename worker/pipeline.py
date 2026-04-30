import subprocess


def cut_video(input_path, start, end, output_path):

    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start),
        "-to", str(end),
        "-i", input_path,

        # FAST CUT (important pour sync)
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",

        "-c:a", "aac",

        "-avoid_negative_ts", "make_zero",
        "-fflags", "+genpts",

        output_path
    ], check=True)