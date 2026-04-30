import os
import time
import subprocess

from app.job_queue import pop_job, ack_job
from app.db import update_job

from storage import download, upload, public_url
from audio.cut import detect_silences, build_segments
from pipeline import cut_video


print("=== WORKER START ===", flush=True)
print("REDIS =", os.getenv("REDIS_URL"), flush=True)


# -------------------------
# UTILS
# -------------------------
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


# -------------------------
# MAIN PROCESS
# -------------------------
def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    print("[JOB START]", job_id, flush=True)

    # 🔥 UPDATE DB → processing
    update_job(job_id, "processing")

    outputs = []
    temp = []

    try:
        for i, path in enumerate(inputs):

            print("[DOWNLOAD]", path, flush=True)

            raw = download(path)

            if not raw:
                raise Exception("Download failed")

            raw_path = f"/tmp/{job_id}_{i}.mp4"

            with open(raw_path, "wb") as f:
                f.write(raw)

            temp.append(raw_path)

            duration = get_duration(raw_path)

            silences = detect_silences(raw_path)
            segments = build_segments(duration, silences)

            print(f"[SEGMENTS] {len(segments)}", flush=True)

            for j, (start, end) in enumerate(segments):

                out = f"/tmp/{job_id}_{i}_{j}.mp4"

                cut_video(raw_path, start, end, out)

                outputs.append(out)
                temp.append(out)

        if not outputs:
            raise Exception("No outputs generated")

        final_path = f"/tmp/{job_id}.mp4"

        print("[CONCAT FINAL]", flush=True)

        concat(outputs, final_path)

        print("[UPLOAD]", flush=True)

        with open(final_path, "rb") as f:
            upload(f"{job_id}.mp4", f)

        url = public_url(f"{job_id}.mp4")

        # 🔥 UPDATE DB → done
        update_job(job_id, "done", url)

        # 🔥 ACK REDIS
        ack_job(job_id)

        print("[DONE]", job_id, flush=True)

    except Exception as e:
        print("[ERROR]", repr(e), flush=True)

        update_job(job_id, "failed")

    finally:
        for f in temp:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass


# -------------------------
# LOOP
# -------------------------
while True:

    try:
        job = pop_job()

        if not job:
            time.sleep(1)
            continue

        print("[POP OK]", job, flush=True)

        process(job)

    except Exception as e:
        print("[WORKER LOOP ERROR]", repr(e), flush=True)
        time.sleep(2)