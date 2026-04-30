import os
import json
import redis
import time

print("=== QUEUE MODULE LOADED ===", flush=True)

REDIS_URL = os.getenv("REDIS_URL")
print("REDIS URL EXISTS:", bool(REDIS_URL), flush=True)

r = redis.from_url(REDIS_URL, decode_responses=True)

print("REDIS CONNECTED OK", flush=True)

if not REDIS_URL:
    raise Exception("REDIS_URL missing")

r = redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_KEY = "jobs:queue"
PROCESSING_KEY = "jobs:processing"
LOCK_TTL = 300  # 5 min safety

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

    r.lpush(QUEUE_KEY, job_id)


# -------------------------
# GET JOB (ATOMIC)
# -------------------------
def pop_job():
    print("[QUEUE] waiting job...", flush=True)

    job_id = r.brpoplpush("jobs:queue", "jobs:processing", timeout=5)

    print("[QUEUE] raw job_id =", job_id, flush=True)

    if not job_id:
        return None

    data = r.hget(f"job:{job_id}", "data")

    print("[QUEUE] job data exists =", bool(data), flush=True)

    if not data:
        return None

    return json.loads(data)


# -------------------------
# ACK SUCCESS
# -------------------------
def ack_job(job_id):
    r.hset(f"job:{job_id}", "status", "done")
    r.lrem(PROCESSING_KEY, 0, job_id)


# -------------------------
# FAIL JOB (RETRY SAFE)
# -------------------------
def fail_job(job_id):
    r.hset(f"job:{job_id}", "status", "queued")
    r.lrem(PROCESSING_KEY, 0, job_id)
    r.lpush(QUEUE_KEY, job_id)


# -------------------------
# CLEANUP STUCK JOBS (optional safety)
# -------------------------
def requeue_stuck():
    stuck = r.lrange(PROCESSING_KEY, 0, -1)

    for job_id in stuck:
        r.lrem(PROCESSING_KEY, 0, job_id)
        r.lpush(QUEUE_KEY, job_id)