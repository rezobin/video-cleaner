import subprocess
import os


def cut_video(input_path, start, end, output_path):
    duration = end - start

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", input_path,
        "-t", str(duration),

        # 🔥 ULTRA IMPORTANT
        "-c", "copy",

        # évite bugs timestamp
        "-avoid_negative_ts", "1",

        output_path
    ]

    subprocess.run(cmd, check=True)


def concat(video_list, output_path):
    list_file = "/tmp/list.txt"

    with open(list_file, "w") as f:
        for v in video_list:
            f.write(f"file '{v}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ]

    subprocess.run(cmd, check=True)

    os.remove(list_file)