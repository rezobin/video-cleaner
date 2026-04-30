import os
import time
import subprocess

from job_queue import pop_job, ack_job
from storage import download, upload, public_url

from audio.cut import detect_silences, build_segments
from pipeline import cut_video


print("=== WORKER START ===", flush=True)
print("REDIS =", os.getenv("REDIS_URL"), flush=True)


def get_duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]).decode().strip())


def concat(files, output_path):

    with open("/tmp/list.txt", "w") as f:
        for v in files:
            f.write(f"file '{v}'\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "/tmp/list.txt",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",

        "-c:a", "aac",
        "-movflags", "+faststart",

        output_path
    ], check=True)


def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    print("[JOB]", job_id, flush=True)

    outputs = []
    temp = []

    for i, path in enumerate(inputs):

        raw = download(path)

        raw_path = f"/tmp/{job_id}_{i}.mp4"

        with open(raw_path, "wb") as f:
            f.write(raw)

        temp.append(raw_path)

        duration = get_duration(raw_path)

        silences = detect_silences(raw_path)
        segments = build_segments(duration, silences)

        for j, (start, end) in enumerate(segments):

            out = f"/tmp/{job_id}_{i}_{j}.mp4"

            cut_video(raw_path, start, end, out)

            outputs.append(out)
            temp.append(out)

    final = f"/tmp/{job_id}.mp4"

    concat(outputs, final)

    with open(final, "rb") as f:
        upload(f"{job_id}.mp4", f)

    ack_job(job_id)

    print("[DONE]", job_id, flush=True)


# -------------------------
# LOOP
# -------------------------
while True:
    job = pop_job()

    if not job:
        time.sleep(1)
        continue

    process(job)