import subprocess

def concat(video_list, output_path):

    list_file = "/tmp/list.txt"

    with open(list_file, "w") as f:
        for v in video_list:
            f.write(f"file '{v}'\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,

        # 🚨 IMPORTANT: no re-encode vidéo
        "-c", "copy",

        output_path
    ], check=True)