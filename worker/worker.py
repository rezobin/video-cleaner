import time
import traceback

from jobs import update
from storage import download, upload, public_url
from pipeline import concat
from audio.cut import remove_silence
from app.supabase_client import supabase


def log(msg):
    print(f"[WORKER] {msg}", flush=True)


def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    log(f"START job={job_id} inputs={inputs}")

    try:
        update(job_id, "processing")
        log("status -> processing")

        cleaned_files = []

        # -------------------------
        # DOWNLOAD + SILENCE CUT
        # -------------------------
        for i, path in enumerate(inputs):

            log(f"Downloading file {i}: {path}")

            raw = download(path)

            raw_path = f"/tmp/{job_id}_{i}_raw.mp4"
            clean_path = f"/tmp/{job_id}_{i}_clean.mp4"

            with open(raw_path, "wb") as f:
                f.write(raw)

            log(f"Wrote raw file: {raw_path}")

            log("Running silence removal...")
            remove_silence(raw_path, clean_path)

            log(f"Clean file created: {clean_path}")

            cleaned_files.append(clean_path)

        # -------------------------
        # CONCAT
        # -------------------------
        output_path = f"/tmp/{job_id}.mp4"

        log(f"Concatenating {len(cleaned_files)} files -> {output_path}")
        concat(cleaned_files, output_path)

        # -------------------------
        # UPLOAD FINAL
        # -------------------------
        final_storage = f"{job_id}.mp4"

        print("[WORKER] Uploading final file...")

        with open(output_path, "rb") as f:
            res = upload(final_storage, f)

        print("[WORKER] Upload response:", res)

        url = public_url(final_storage)

        print("[WORKER] Generated public URL:", url)

        update(job_id, "done", url)

        print("[WORKER] DONE:", job_id)

    except Exception as e:
        log("WORKER ERROR:")
        log(str(e))
        log(traceback.format_exc())

        update(job_id, "failed")


log("WORKER STARTED 🟢")

while True:

    try:
        res = supabase.table("jobs") \
            .select("*") \
            .eq("status", "queued") \
            .limit(1) \
            .execute()

        jobs = res.data

        if jobs:
            log(f"Job found: {jobs[0]['id']}")
            process(jobs[0])
        else:
            log("No job")

    except Exception as e:
        log("LOOP ERROR")
        log(str(e))

    time.sleep(2)