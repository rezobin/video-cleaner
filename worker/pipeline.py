import subprocess


def cut_video(input_path, start, end, output_path):
    print(f"[CUT] {start} → {end}", flush=True)

    subprocess.run([
        "ffmpeg",
        "-y",

        "-ss", str(start),
        "-to", str(end),

        "-i", input_path,

        "-c", "copy",  # 🔥 NO RE-ENCODE → SPEED
        "-avoid_negative_ts", "1",

        output_path
    ], check=True)