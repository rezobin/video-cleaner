import time
import os

from jobs import update
from storage import upload, public_url

from audio.cut import detect_silences, build_segments
from pipeline import concat

from queue import pop_job_safe, ack_job


MAX_INPUT_FILES = 10


def process(job):

    job_id = job["id"]
    inputs = job["input_paths"][:MAX_INPUT_FILES]

    print(f"[WORKER] START {job_id}")

    try:
        update(job_id, "processing")

        all_segments = []

        for path in inputs:

            duration = float(os.popen(
                f"ffprobe -v error -show_entries format=duration "
                f"-of default=noprint_wrappers=1:nokey=1 '{path}'"
            ).read().strip())

            silences = detect_silences(path)
            segments = build_segments(duration, silences)

            for (start, end) in segments:
                all_segments.append((path, start, end))

        if not all_segments:
            raise Exception("No segments")

        output_path = f"/tmp/{job_id}.mp4"

        concat(all_segments, output_path)

        with open(output_path, "rb") as f:
            upload(f"{job_id}.mp4", f)

        url = public_url(f"{job_id}.mp4")

        update(job_id, "done", url)

        ack_job(job_id)

        print("[DONE]", url)

    except Exception as e:
        print("[ERROR]", e)
        update(job_id, "failed")


print("[WORKER START]")

while True:
    job = pop_job_safe()

    print("[JOB RECEIVED]", job["id"])

    process(job)