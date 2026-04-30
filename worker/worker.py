import time
import os

from jobs import update, get_job
from storage import upload, public_url, get_signed_url

from audio.cut import (
    detect_silences,
    build_segments
)

from pipeline import concat


MAX_INPUT_FILES = 10


def process(job):

    job_id = job["id"]
    inputs = job["input_paths"][:MAX_INPUT_FILES]

    print(f"[WORKER] START {job_id}")

    temp_files = []

    try:
        update(job_id, "processing")

        all_segments = []

        for i, path in enumerate(inputs):

            print(f"[INPUT] {path}")

            # 🔥 on récupère une URL signée (pas de download)
            video_url = get_signed_url(path)

            # durée vidéo via ffprobe (URL directe)
            duration = float(os.popen(
                f"ffprobe -v error -show_entries format=duration "
                f"-of default=noprint_wrappers=1:nokey=1 '{video_url}'"
            ).read().strip())

            # détection silence directement sur la vidéo
            silences = detect_silences(video_url)

            segments = build_segments(duration, silences)

            print(f"[SEGMENTS] video {i}: {len(segments)}")

            for (start, end) in segments:
                all_segments.append((video_url, start, end))

        if not all_segments:
            raise Exception("No segments")

        final_path = f"/tmp/{job_id}.mp4"
        temp_files.append(final_path)

        print("[FFMPEG GLOBAL CONCAT]")

        concat(all_segments, final_path)

        print("[UPLOAD]")

        with open(final_path, "rb") as f:
            upload(f"{job_id}.mp4", f)

        url = public_url(f"{job_id}.mp4")

        update(job_id, "done", url)

        print("[DONE]", url)

    except Exception as e:
        print("[ERROR]", e)
        update(job_id, "failed")

    finally:
        print("[CLEANUP]")
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass


print("[WORKER START]")

while True:
    job = get_job()

    if not job:
        time.sleep(2)
        continue

    process(job)