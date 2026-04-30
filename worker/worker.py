import time
import os

print("=== WORKER BOOT ===", flush=True)
print("REDIS_URL =", os.getenv("REDIS_URL"), flush=True)

import subprocess

from job_queue import pop_job, ack_job, fail_job
from storage import download, upload, public_url

from audio.cut import detect_silences, build_segments
from pipeline import cut_video

MAX_FILES = 3


def get_duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]).decode().strip())


def concat_final(files, output_path):

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

    print(f"[WORKER] START {job_id}")

    temp_files = []

    try:
        outputs = []

        for i, path in enumerate(inputs):

            raw_path = f"/tmp/{job_id}_{i}.mp4"

            raw = download(path)
            if not raw:
                raise Exception("Download failed")

            with open(raw_path, "wb") as f:
                f.write(raw)

            temp_files.append(raw_path)

            duration = get_duration(raw_path)

            silences = detect_silences(raw_path)
            segments = build_segments(duration, silences)

            print(f"[SEGMENTS] {len(segments)}")

            for j, (start, end) in enumerate(segments):

                out = f"/tmp/{job_id}_{i}_{j}.mp4"

                cut_video(raw_path, start, end, out)

                outputs.append(out)
                temp_files.append(out)

        if not outputs:
            raise Exception("No outputs")

        final_path = f"/tmp/{job_id}.mp4"

        concat_final(outputs, final_path)

        with open(final_path, "rb") as f:
            upload(f"{job_id}.mp4", f)

        url = public_url(f"{job_id}.mp4")

        ack_job(job_id)

        print("[DONE]", url)

    except Exception as e:
        print("[ERROR]", e)
        fail_job(job_id)

    finally:
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass



print("[WORKER START]")
print("REDIS_URL =", os.getenv("REDIS_URL"))

while True:
    try:
        print("[WORKER] polling Redis...")

        job = pop_job()

        job = pop_job()

        print("[WORKER DEBUG] received job =", job)

        if not job:
            time.sleep(2)
            continue

        print("[WORKER] raw job =", job)

        print(f"[WORKER] processing job {job.get('id')}")

        process(job)

    except Exception as e:
        print("[WORKER LOOP ERROR]", repr(e))
        time.sleep(2)