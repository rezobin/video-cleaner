import time

from jobs import update
from storage import download, upload, public_url
from pipeline import concat
from audio.cut import remove_silence
from app.supabase_client import supabase

def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    try:
        update(job_id, "processing")

        cleaned_files = []

        # -------------------------
        # DOWNLOAD + SILENCE CUT
        # -------------------------
        for i, path in enumerate(inputs):

            raw = download(path)

            raw_path = f"/tmp/{job_id}_{i}_raw.mp4"
            clean_path = f"/tmp/{job_id}_{i}_clean.mp4"

            with open(raw_path, "wb") as f:
                f.write(raw)

            remove_silence(raw_path, clean_path)

            cleaned_files.append(clean_path)

        # -------------------------
        # CONCAT
        # -------------------------
        output_path = f"/tmp/{job_id}.mp4"

        concat(cleaned_files, output_path)

        # -------------------------
        # UPLOAD FINAL
        # -------------------------
        final_storage = f"{job_id}.mp4"

        with open(output_path, "rb") as f:
            upload(final_storage, f)

        url = public_url(final_storage)

        update(job_id, "done", url)

        print("DONE:", job_id)

    except Exception as e:
        print("WORKER ERROR:", e)
        update(job_id, "failed")


print("WORKER STARTED 🟢")

while True:

    res = supabase.table("jobs") \
        .select("*") \
        .eq("status", "queued") \
        .limit(1) \
        .execute()

    jobs = res.data

    if jobs:
        process(jobs[0])

    time.sleep(2)