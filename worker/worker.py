import os
import time
import subprocess
import redis

from app.job_queue import pop_job, ack_job
from app.db import update_job

from storage import download, upload, public_url
from audio.cut import detect_silences, build_segments
from pipeline import cut_video


print("=== WORKER START ===", flush=True)

# -------------------------
# REDIS SAFE INIT (IMPORTANT FIX)
# -------------------------
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise Exception("REDIS_URL missing")

r = redis.from_url(REDIS_URL, decode_responses=True)


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


def set_progress(job_id, value):
    try:
        r.hset(f"job:{job_id}", "progress", int(value))
        r.hset(f"job:{job_id}", "status", "processing")
    except Exception as e:
        print("[REDIS PROGRESS ERROR]", repr(e), flush=True)


# -------------------------
# CONCAT FIXED
# -------------------------
def concat(files, output_path):
    print("[CONCAT START]", flush=True)

    with open("/tmp/list.txt", "w") as f:
        for v in files:
            f.write(f"file '{v}'\n")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "/tmp/list.txt",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",

        "-c:a", "aac",
        "-b:a", "128k",

        "-movflags", "+faststart",

        output_path
    ], check=True)

    print("[CONCAT DONE]", flush=True)


# -------------------------
# PROCESS JOB
# -------------------------
def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    print("[JOB START]", job_id, flush=True)

    update_job(job_id, "processing")
    set_progress(job_id, 5)

    temp = []

    try:
        all_segments_files = []

        for i, path in enumerate(inputs):

            print("[DOWNLOAD]", path, flush=True)

            raw = download(path)

            if not raw:
                raise Exception("Download failed")

            raw_path = f"/tmp/{job_id}_{i}.mp4"

            with open(raw_path, "wb") as f:
                f.write(raw)

            temp.append(raw_path)

            set_progress(job_id, 15 + i * 10)

            duration = get_duration(raw_path)
            print("[DURATION]", duration, flush=True)

            silences = detect_silences(raw_path)
            segments = build_segments(duration, silences)

            print("[SEGMENTS]", len(segments), flush=True)

            for j, (start, end) in enumerate(segments):

                out = f"/tmp/{job_id}_{i}_{j}.mp4"

                cut_video(raw_path, start, end, out)

                all_segments_files.append(out)
                temp.append(out)

            set_progress(job_id, 50)

        final_path = f"/tmp/{job_id}.mp4"

        print("[FINAL CONCAT]", flush=True)

        concat(all_segments_files, final_path)

        set_progress(job_id, 80)

        print("[UPLOAD]", flush=True)

        with open(final_path, "rb") as f:
            upload(f"{job_id}.mp4", f)

        url = public_url(f"{job_id}.mp4")

        update_job(job_id, "done", url)
        ack_job(job_id)

        set_progress(job_id, 100)

        print("[DONE]", job_id, flush=True)

    except Exception as e:
        print("[ERROR]", repr(e), flush=True)

        update_job(job_id, "failed")

        try:
            r.hset(f"job:{job_id}", "status", "failed")
        except:
            pass

    finally:
        for f in temp:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass


# -------------------------
# LOOP (SAFE)
# -------------------------
while True:
    try:
        job = pop_job()

        if not job:
            time.sleep(1)
            continue

        process(job)

    except Exception as e:
        print("[WORKER LOOP ERROR]", repr(e), flush=True)
        time.sleep(2)