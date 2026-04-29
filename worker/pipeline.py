import subprocess


def concat_filter_complex(input_path, segments, output_path):

    filter_parts = []
    inputs = []

    for i, (start, end) in enumerate(segments):

        inputs.append("-ss")
        inputs.append(str(start))
        inputs.append("-to")
        inputs.append(str(end))
        inputs.append("-i")
        inputs.append(input_path)

        filter_parts.append(f"[{i}:v:0][{i}:a:0]")

    concat_filter = "".join(filter_parts) + f"concat=n={len(segments)}:v=1:a=1[outv][outa]"

    cmd = ["ffmpeg", "-y"]

    cmd += inputs

    cmd += [
        "-filter_complex", concat_filter,
        "-map", "[outv]",
        "-map", "[outa]",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",

        "-c:a", "aac",

        "-movflags", "+faststart",

        output_path
    ]

    subprocess.run(cmd, check=True)