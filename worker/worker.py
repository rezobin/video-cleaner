import time
import os
from concurrent.futures import ThreadPoolExecutor

from jobs import update, get_job
from storage import download, upload, public_url
from pipeline import concat
from audio.cut import remove_silence

MAX_WORKERS = 2  # tu peux monter à 4 sur 2GB


def process_file(job_id, i, path):
    print(f"[WORKER] Downloading {path}")

    raw = download(path)
    if raw is None:
        raise Exception("Download failed")

    raw_path = f"/tmp/{job_id}_{i}_raw.mp4"
    clean_path = f"/tmp/{job_id}_{i}_clean.mp4"

    with open(raw_path, "wb") as f:
        f.write(raw)

    print(f"[WORKER] Processing silence removal {i}")
    remove_silence(raw_path, clean_path)

    if not os.path.exists(clean_path):
        raise Exception("Clean file not created")

    return raw_path, clean_path


def process(job):
    job_id = job["id"]
    inputs = job["input_paths"]

    print(f"[WORKER] START job={job_id}")

    temp_files = []

    try:
        update(job_id, "processing")

        cleaned_files = []

        # 🔥 PARALLEL PROCESSING
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(process_file, job_id, i, path)
                for i, path in enumerate(inputs)
            ]

            for future in futures:
                raw_path, clean_path = future.result()
                temp_files.append(raw_path)
                temp_files.append(clean_path)
                cleaned_files.append(clean_path)

        print("[WORKER] All files processed")

        # -------------------------
        # CONCAT
        # -------------------------
        output_path = f"/tmp/{job_id}.mp4"

        print("[WORKER] Concatenating...")
        concat(cleaned_files, output_path)

        if not os.path.exists(output_path):
            raise Exception("Concat failed")

        temp_files.append(output_path)

        # -------------------------
        # UPLOAD
        # -------------------------
        final_storage = f"{job_id}.mp4"

        print("[WORKER] Uploading...")
        with open(output_path, "rb") as f:
            upload(final_storage, f)

        url = public_url(final_storage)

        if not url:
            raise Exception("URL generation failed")

        update(job_id, "done", url)

        print("[WORKER] DONE", job_id)

    except Exception as e:
        print("[WORKER ERROR]", e)
        update(job_id, "failed")

    finally:
        print("[WORKER] Cleaning temp files")
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                print("[CLEAN ERROR]", e)


print("[WORKER] STARTED")

while True:
    job = get_job()

    if not job:
        time.sleep(2)
        continue

    process(job)