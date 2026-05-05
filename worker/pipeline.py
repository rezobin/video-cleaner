import subprocess

def cut_video(input_path, start, end, output_path):
    print(f"[CUT] {start} → {end}", flush=True)

    subprocess.run([
        "ffmpeg",
        "-y",

        "-ss", str(start),
        "-to", str(end),
        "-i", input_path,

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",

        "-c:a", "aac",
        "-b:a", "128k",

        "-threads", "2"
        ,output_path
    ],
    check=True,
    timeout=120  # 🔥 IMPORTANT
    )