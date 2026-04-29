import time
import os
import subprocess

from jobs import update, get_job
from storage import download, upload, public_url
from pipeline import concat
from audio.cut import remove_silence


# -------------------------
# CONFIG PERF
# -------------------------
PROXY_HEIGHT = 360  # 360 si tu veux encore plus rapide
PADDING = 0.2


def create_proxy(input_path, output_path):
    """
    Génère une version légère pour analyse rapide
    """
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"scale=-2:{PROXY_HEIGHT}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "64k",
        output_path
    ], check=True)


def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    print(f"[WORKER] START job={job_id} inputs={inputs}")

    temp_files = []

    try:
        update(job_id, "processing")

        cleaned_files = []

        # -------------------------
        # STEP 1: DOWNLOAD + PROXY
        # -------------------------
        for i, path in enumerate(inputs):

            print(f"[WORKER] Downloading file {i}: {path}")

            raw = download(path)

            if not raw:
                raise Exception("Download failed")

            raw_path = f"/tmp/{job_id}_{i}_raw.mp4"
            proxy_path = f"/tmp/{job_id}_{i}_proxy.mp4"
            clean_path = f"/tmp/{job_id}_{i}_clean.mp4"

            with open(raw_path, "wb") as f:
                f.write(raw)

            temp_files.append(raw_path)

            print("[WORKER] Creating proxy...")
            create_proxy(raw_path, proxy_path)
            temp_files.append(proxy_path)

            # -------------------------
            # STEP 2: SILENCE REMOVAL (proxy audio)
            # -------------------------
            print("[WORKER] Running silence removal on proxy...")
            remove_silence(proxy_path, clean_path)

            if not os.path.exists(clean_path):
                raise Exception("Clean file not created")

            size = os.path.getsize(clean_path)
            print(f"[WORKER] Clean file size: {size}")

            if size == 0:
                raise Exception("Clean file empty")

            cleaned_files.append(clean_path)
            temp_files.append(clean_path)

        print(f"[WORKER] Clean segments ready: {cleaned_files}")

        # -------------------------
        # STEP 3: CONCAT (proxy level)
        # -------------------------
        output_path = f"/tmp/{job_id}_proxy.mp4"

        print("[WORKER] Concat proxy segments...")
        concat(cleaned_files, output_path)

        temp_files.append(output_path)

        # -------------------------
        # STEP 4: UPSCALE FINAL (FULL RES APPLY SAME CUTS)
        # -------------------------
        final_path = f"/tmp/{job_id}.mp4"

        print("[WORKER] Rebuilding full res output...")

        subprocess.run([
            "ffmpeg", "-y",
            "-i", output_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            final_path
        ], check=True)

        temp_files.append(final_path)

        # -------------------------
        # UPLOAD
        # -------------------------
        final_storage = f"{job_id}.mp4"

        print("[WORKER] Uploading final file...")

        with open(final_path, "rb") as f:
            res = upload(final_storage, f)

        print("[WORKER] Upload response:", res)

        if hasattr(res, "error") and res.error:
            raise Exception(res.error)

        url = public_url(final_storage)

        print("[WORKER] URL:", url)

        update(job_id, "done", url)

        print("[WORKER] DONE:", job_id)

    except Exception as e:
        print("[WORKER ERROR]:", e)
        update(job_id, "failed")

    finally:
        print("[WORKER] Cleaning temp files...")
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    print(f"[WORKER] Deleted: {f}")
            except Exception as e:
                print(f"[WORKER] Cleanup error: {e}")


print("[WORKER] STARTED 🟢")

while True:
    job = get_job()

    if not job:
        print("[WORKER] No job")
        time.sleep(2)
        continue

    print("[WORKER] PICKED:", job["id"])

    try:
        process(job)
    except Exception as e:
        print("[WORKER] FATAL:", e)