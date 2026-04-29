import subprocess
import os


def cut_video(input_path, start, end, output_path):
    duration = end - start

    cmd = [
        "ffmpeg", "-y",

        "-i", input_path,        # 🔴 IMPORTANT: input AVANT -ss
        "-ss", str(start),
        "-t", str(duration),

        "-avoid_negative_ts", "1",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",

        "-c:a", "aac",
        "-b:a", "128k",

        output_path
    ]

    print("[FFMPEG CUT]", " ".join(cmd))

    subprocess.run(cmd, check=True, timeout=120)

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

        # 🔴 TEMP pour stabilité
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "20",
        "-c:a", "aac",

        output_path
    ]

    print("[FFMPEG CONCAT]", " ".join(cmd))

    subprocess.run(cmd, check=True, timeout=180)

    os.remove(list_file)