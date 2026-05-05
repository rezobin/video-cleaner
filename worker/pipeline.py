import subprocess


def build_filter(segments):
    """
    Génère le filter_complex ffmpeg à partir des segments
    """

    parts = []
    concat_inputs = []

    for i, (start, end) in enumerate(segments):
        parts.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];"
        )
        parts.append(
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];"
        )

        concat_inputs.append(f"[v{i}][a{i}]")

    concat_str = "".join(concat_inputs)

    parts.append(
        f"{concat_str}concat=n={len(segments)}:v=1:a=1[outv][outa]"
    )

    return "".join(parts)


def process_video(input_path, segments, output_path):
    """
    Coupe et concat en UNE SEULE commande ffmpeg
    """

    if not segments:
        raise Exception("No segments")

    filter_complex = build_filter(segments)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",

        # encodage rapide
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",

        "-c:a", "aac",
        "-movflags", "+faststart",

        output_path
    ]

    subprocess.run(cmd, check=True)