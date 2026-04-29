import subprocess
import os

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

        # 🔴 IMPORTANT : éviter re-encode
        "-c", "copy",

        output_path
    ]

    subprocess.run(cmd, check=True)

    os.remove(list_file)