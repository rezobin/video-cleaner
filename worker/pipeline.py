import subprocess

def cut_video(input_path, start, end, output_path):

    subprocess.run([
        "ffmpeg", "-y",

        "-ss", str(start),
        "-to", str(end),
        "-i", input_path,

        # IMPORTANT: copy codecs (NO RE-ENCODE ici)
        "-c", "copy",

        output_path
    ], check=True)


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

        # ONE SINGLE ENCODE ONLY HERE
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",

        "-c:a", "aac",

        output_path
    ], check=True)