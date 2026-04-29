import time
import os

from jobs import update, get_job
from storage import download, upload, public_url

from audio.cut import (
    detect_silences,
    build_segments,
    get_video_duration
)

from pipeline import cut_video, concat


def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    print(f"[WORKER] START job={job_id}")

    temp_files = []

    try:
        update(job_id, "processing")

        final_segments = []

        # -------------------------
        # PROCESS EACH VIDEO
        # -------------------------
        for i, path in enumerate(inputs):

            raw_path = f"/tmp/{job_id}_{i}.mp4"

            print(f"[WORKER] downloading {path}")
            raw = download(path)

            if raw is None:
                raise Exception("Download failed")

            with open(raw_path, "wb") as f:
                f.write(raw)

            temp_files.append(raw_path)

            # -------------------------
            # SILENCE DETECTION
            # -------------------------
            print("[WORKER] detect silence")
            silences = detect_silences(raw_path)

            duration = get_video_duration(raw_path)

            segments = build_segments(duration, silences)

            print(f"[WORKER] segments: {segments}")
            print(f"[WORKER] Total segments: {len(segments)}")

            # -------------------------
            # CUT VIDEO
            # -------------------------
            for j, (start, end) in enumerate(segments):

                print(f"[WORKER] Processing segment {start} → {end}")

                out = f"/tmp/{job_id}_{i}_{j}.mp4"

                cut_video(raw_path, start, end, out)

                final_segments.append(out)
                temp_files.append(out)

        if not final_segments:
            raise Exception("No segments produced")

        # -------------------------
        # CONCAT FINAL
        # -------------------------
        output_path = f"/tmp/{job_id}.mp4"

        print("[WORKER] concat final")
        concat(final_segments, output_path)

        temp_files.append(output_path)

        # -------------------------
        # UPLOAD
        # -------------------------
        final_storage = f"{job_id}.mp4"

        print("[WORKER] uploading")

        with open(output_path, "rb") as f:
            upload(final_storage, f)

        url = public_url(final_storage)

        if not url:
            raise Exception("URL generation failed")

        update(job_id, "done", url)

        print("[WORKER] DONE")

    except Exception as e:
        print("[WORKER ERROR]", e)
        update(job_id, "failed")

    finally:
        print("[WORKER] cleanup")
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                print("[CLEAN ERROR]", e)


print("[WORKER] START")

while True:
    job = get_job()

    if not job:
        print("[WORKER] No job")
        time.sleep(2)
        continue

    process(job)