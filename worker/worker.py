import time
import os

from jobs import update, get_job
from storage import download, upload, public_url
from pipeline import concat
from audio.cut import remove_silence


def process(job):
    job_id = job["id"]
    inputs = job["input_paths"]

    print(f"[WORKER] START job={job_id} inputs={inputs}")

    temp_files = []

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

            temp_files.append(raw_path)

            print(f"[WORKER] Wrote raw file: {raw_path}")

            print("[WORKER] Running silence removal...")
            remove_silence(raw_path, clean_path)

            if not os.path.exists(clean_path):
                raise Exception(f"Clean file NOT created: {clean_path}")

            size = os.path.getsize(clean_path)
            print(f"[WORKER] Clean file size: {size} bytes")

            if size == 0:
                raise Exception(f"Clean file EMPTY: {clean_path}")

            cleaned_files.append(clean_path)
            temp_files.append(clean_path)

        print(f"[WORKER] Cleaned files ready: {cleaned_files}")

        # -------------------------
        # CONCAT
        # -------------------------
        output_path = f"/tmp/{job_id}.mp4"

        print("[WORKER] Running concat...")
        concat(cleaned_files, output_path)

        if not os.path.exists(output_path):
            raise Exception("Concat output not created")

        temp_files.append(output_path)

        print(f"[WORKER] Concat output exists: {output_path}")

        # -------------------------
        # UPLOAD FINAL
        # -------------------------
        final_storage = f"{job_id}.mp4"

        print("[WORKER] Uploading final file...")

        with open(output_path, "rb") as f:
            res = upload(final_storage, f)

        print("[WORKER] Upload response:", res)

        if res is None:
            raise Exception("Upload returned None")

        url = public_url(final_storage)

        if not url:
            raise Exception("Public URL generation failed")

        print("[WORKER] Generated public URL:", url)

        update(job_id, "done", url)

        print("[WORKER] DONE:", job_id)

    except Exception as e:
        print("[WORKER ERROR]:", e)
        update(job_id, "failed")

    finally:
        # 🔴 CLEANUP (CRUCIAL SUR RENDER)
        print("[WORKER] Cleaning temp files...")
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    print(f"[WORKER] Deleted: {f}")
            except Exception as e:
                print(f"[WORKER] Cleanup error: {e}")


print("[WORKER] WORKER STARTED 🟢")

while True:
    job = get_job()

    if not job:
        print("[WORKER] No job")
        time.sleep(2)
        continue

    print("[WORKER] START:", job["id"])

    try:
        process(job)
    except Exception as e:
        print("[WORKER] FATAL ERROR:", e)