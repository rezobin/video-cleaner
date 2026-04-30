import os
import json
import redis
import time

REDIS_URL = os.getenv("REDIS_URL")

r = redis.from_url(REDIS_URL, decode_responses=True)

QUEUE = "video_jobs"
PROCESSING = "video_processing"


# -------------------------
# PRODUCER
# -------------------------
def push_job(job: dict):
    r.lpush(QUEUE, json.dumps(job))


# -------------------------
# CONSUMER SAFE (ATOMIC)
# -------------------------
def pop_job_safe():

    while True:
        # atomique : move queue → processing
        job = r.brpoplpush(QUEUE, PROCESSING, timeout=5)

        if job:
            return json.loads(job)

        time.sleep(0.2)


# -------------------------
# ACK (SUCCESS)
# -------------------------
def ack_job(job_id: str):
    items = r.lrange(PROCESSING, 0, -1)

    for item in items:
        job = json.loads(item)
        if job["id"] == job_id:
            r.lrem(PROCESSING, 1, item)
            return


# -------------------------
# FAILSAFE (OPTIONNEL FUTUR)
# -------------------------
def requeue_stuck_jobs():
    # si worker crash → requeue manuel possible
    items = r.lrange(PROCESSING, 0, -1)

    for item in items:
        r.lpush(QUEUE, item)
        r.lrem(PROCESSING, 1, item)