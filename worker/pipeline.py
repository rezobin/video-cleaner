import subprocess


def cut_video(input_path, start, end, output_path):
    # (optionnel, pas utilisé ici)
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start),
        "-to", str(end),
        "-i", input_path,
        "-c", "copy",
        output_path
    ], check=True)


def concat(input_path, segments, output_path):

    if not segments:
        raise Exception("No segments provided")

    filters = []
    v_inputs = []
    a_inputs = []

    for i, (start, end) in enumerate(segments):

        filters.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];"
        )
        filters.append(
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];"
        )

        v_inputs.append(f"[v{i}]")
        a_inputs.append(f"[a{i}]")

    filter_complex = "".join(filters) + \
        "".join(v_inputs) + "".join(a_inputs) + \
        f"concat=n={len(segments)}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",

        "-c:a", "aac",

        output_path
    ]

    subprocess.run(cmd, check=True)