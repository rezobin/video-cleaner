import time
import os

from job_queue import pop_job, ack_job, fail_job
from storage import download, upload, public_url

from audio.cut import detect_silences, build_segments
from pipeline import cut_video, concat

MAX_CONCURRENT_FILES = 3  # 🔥 limite CPU FFmpeg

def process(job):

    job_id = job["id"]
    inputs = job["input_paths"]

    print(f"[WORKER] START {job_id}")

    temp_files = []

    try:
        final_outputs = []

        for i, path in enumerate(inputs):

            raw_path = f"/tmp/{job_id}_{i}.mp4"

            raw = download(path)
            if not raw:
                raise Exception("Download failed")

            with open(raw_path, "wb") as f:
                f.write(raw)

            temp_files.append(raw_path)

            duration = float(os.popen(
                f"ffprobe -v error -show_entries format=duration "
                f"-of default=noprint_wrappers=1:nokey=1 {raw_path}"
            ).read().strip())

            silences = detect_silences(raw_path)
            segments = build_segments(duration, silences)

            if not segments:
                continue

            output_path = f"/tmp/{job_id}_{i}_out.mp4"

            concat(raw_path, segments, output_path)

            final_outputs.append(output_path)
            temp_files.append(output_path)

        if not final_outputs:
            raise Exception("No output generated")

        final_path = f"/tmp/{job_id}.mp4"

        with open("/tmp/list.txt", "w") as f:
            for v in final_outputs:
                f.write(f"file '{v}'\n")

        os.system(f"""
            ffmpeg -y -f concat -safe 0 -i /tmp/list.txt \
            -c:v libx264 -preset veryfast -crf 22 \
            -c:a aac -movflags +faststart {final_path}
        """)

        with open(final_path, "rb") as f:
            upload(f"{job_id}.mp4", f)

        url = public_url(f"{job_id}.mp4")

        ack_job(job_id)

        print("[DONE]", url)

    except Exception as e:
        print("[ERROR]", e)
        fail_job(job_id)

    finally:
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass


print("[WORKER START]")

while True:
    job = pop_job()

    if not job:
        time.sleep(2)
        continue

    process(job)