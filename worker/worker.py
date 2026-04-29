import time
import os

from jobs import update
from storage import download, upload, public_url
from pipeline import concat
from audio.cut import remove_silence
from app.supabase_client import supabase


def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    print(f"[WORKER] START job={job_id} inputs={inputs}")

    try:
        update(job_id, "processing")

        cleaned_files = []

        # -------------------------
        # DOWNLOAD + SILENCE CUT
        # -------------------------
        for i, path in enumerate(inputs):

            print(f"[WORKER] Downloading file {i}: {path}")

            raw = download(path)

            raw_path = f"/tmp/{job_id}_{i}_raw.mp4"
            clean_path = f"/tmp/{job_id}_{i}_clean.mp4"

            with open(raw_path, "wb") as f:
                f.write(raw)

            print(f"[WORKER] Wrote raw file: {raw_path}")

            # 🔴 STEP CRITIQUE
            print("[WORKER] Running silence removal...")
            remove_silence(raw_path, clean_path)

            # ✅ CHECK FILE EXISTS
            if not os.path.exists(clean_path):
                raise Exception(f"Clean file NOT created: {clean_path}")

            size = os.path.getsize(clean_path)

            print(f"[WORKER] Clean file size: {size} bytes")

            if size == 0:
                raise Exception(f"Clean file EMPTY: {clean_path}")

            cleaned_files.append(clean_path)

        print(f"[WORKER] Cleaned files ready: {cleaned_files}")

        # -------------------------
        # CONCAT
        # -------------------------
        output_path = f"/tmp/{job_id}.mp4"

        print("[WORKER] Running concat...")
        concat(cleaned_files, output_path)

        if not os.path.exists(output_path):
            raise Exception("Concat output not created")

        print(f"[WORKER] Concat output exists: {output_path}")

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
        print("[WORKER ERROR]:", e)
        update(job_id, "failed")


print("[WORKER] WORKER STARTED 🟢")

while True:

    res = supabase.table("jobs") \
        .select("*") \
        .eq("status", "queued") \
        .limit(1) \
        .execute()

    jobs = res.data

    if jobs:
        print("[WORKER] Job found:", jobs[0]["id"])
        process(jobs[0])
    else:
        print("[WORKER] No job")

    time.sleep(2)