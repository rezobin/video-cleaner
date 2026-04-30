import subprocess


def concat(segments, output_path):

    inputs = []
    filter_parts = []
    v_parts = []
    a_parts = []

    for i, (path, start, end) in enumerate(segments):

        inputs.extend(["-i", path])

        filter_parts.append(
            f"[{i}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];"
        )
        filter_parts.append(
            f"[{i}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];"
        )

        v_parts.append(f"[v{i}]")
        a_parts.append(f"[a{i}]")

    filter_complex = "".join(filter_parts) + \
        "".join(v_parts) + "".join(a_parts) + \
        f"concat=n={len(segments)}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",

        "-c:v", "libx264",
        "-preset", "ultrafast",   # 🔥 gain immédiat
        "-crf", "23",

        "-c:a", "aac",

        output_path
    ]

    subprocess.run(cmd, check=True)