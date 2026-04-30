import time
import os

from jobs import update, get_job
from storage import download, upload, public_url

from audio.cut import (
    detect_silences,
    build_segments
)

from pipeline import concat_filter_complex


def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    print(f"[WORKER] START {job_id}")

    temp_files = []

    try:
        update(job_id, "processing")

        all_outputs = []

        for i, path in enumerate(inputs):

            raw_path = f"/tmp/{job_id}_{i}.mp4"

            print("[DL]", path)

            raw = download(path)

            if not raw:
                raise Exception("Download failed")

            with open(raw_path, "wb") as f:
                f.write(raw)

            temp_files.append(raw_path)

            # durée vidéo
            duration = float(os.popen(
                f"ffprobe -v error -show_entries format=duration "
                f"-of default=noprint_wrappers=1:nokey=1 {raw_path}"
            ).read().strip())

            print("[SILENCE DETECTION]")
            silences = detect_silences(raw_path)

            segments = build_segments(duration, silences)

            print(f"[SEGMENTS] {len(segments)}")

            if len(segments) == 0:
                continue

            output_path = f"/tmp/{job_id}_{i}_out.mp4"

            print("[FILTER COMPLEX CUT]")

            concat_filter_complex(raw_path, segments, output_path)

            all_outputs.append(output_path)
            temp_files.append(output_path)

        if not all_outputs:
            raise Exception("No outputs generated")

        final_path = f"/tmp/{job_id}.mp4"

        # concat final simple
        with open("/tmp/list.txt", "w") as f:
            for v in all_outputs:
                f.write(f"file '{v}'\n")

        os.system(f"""
            ffmpeg -y -f concat -safe 0 -i /tmp/list.txt \
            -c:v libx264 -preset fast -crf 20 \
            -c:a aac -movflags +faststart {final_path}
        """)

        with open(final_path, "rb") as f:
            upload(f"{job_id}.mp4", f)

        url = public_url(f"{job_id}.mp4")

        update(job_id, "done", url)

        print("[DONE]", url)

    except Exception as e:
        print("[ERROR]", e)
        update(job_id, "failed")

    finally:
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