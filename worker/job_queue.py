import os
import json
import redis
import time

print("=== QUEUE MODULE LOADED ===", flush=True)

REDIS_URL = os.getenv("REDIS_URL")
print("REDIS URL EXISTS:", bool(REDIS_URL), flush=True)

if not REDIS_URL:
    raise Exception("REDIS_URL missing")

r = redis.from_url(REDIS_URL, decode_responses=True)
print("REDIS CONNECTED OK", flush=True)

QUEUE_KEY = "jobs:queue"
PROCESSING_KEY = "jobs:processing"


# -------------------------
# PUSH JOB
# -------------------------
def push_job(job: dict):
    job_id = job["id"]

    r.hset(f"job:{job_id}", mapping={
        "data": json.dumps(job),
        "status": "queued",
        "ts": str(time.time())
    })

    print("[PUSH DEBUG] BEFORE LPUSH", job_id, flush=True)
    r.lpush(QUEUE_KEY, job_id)
    print("[PUSH DEBUG] AFTER LPUSH", r.llen(QUEUE_KEY), flush=True)


# -------------------------
# POP JOB (ATOMIC)
# -------------------------
def pop_job():
    print("[QUEUE] waiting job...", flush=True)

    job_id = r.brpoplpush(QUEUE_KEY, PROCESSING_KEY, timeout=5)

    print("[QUEUE] raw job_id =", job_id, flush=True)

    if not job_id:
        return None

    data = r.hget(f"job:{job_id}", "data")

    print("[QUEUE] job data exists =", bool(data), flush=True)

    if not data:
        return None

    return json.loads(data)


# -------------------------
# ACK
# -------------------------
def ack_job(job_id):
    r.hset(f"job:{job_id}", "status", "done")
    r.lrem(PROCESSING_KEY, 0, job_id)


# -------------------------
# FAIL
# -------------------------
def fail_job(job_id):
    r.hset(f"job:{job_id}", "status", "queued")
    r.lrem(PROCESSING_KEY, 0, job_id)
    r.lpush(QUEUE_KEY, job_id)