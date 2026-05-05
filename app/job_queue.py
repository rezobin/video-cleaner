import os
import json
import redis
import time

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise Exception("REDIS_URL missing")

print("[QUEUE INIT]", REDIS_URL, flush=True)

# ✅ FIX SIMPLE & ROBUSTE
r = redis.from_url(
    REDIS_URL,
    decode_responses=True
)

QUEUE_KEY = "jobs:queue"


def push_job(job: dict):
    job_id = job["id"]

    r.hset(f"job:{job_id}", mapping={
        "data": json.dumps(job),
        "status": "queued",
        "ts": str(time.time())
    })

    r.rpush(QUEUE_KEY, job_id)

    print("[PUSH]", job_id, flush=True)


def pop_job():
    print("[POP WAITING]", flush=True)

    res = r.blpop(QUEUE_KEY, timeout=1)

    print("[POP RAW]", res, flush=True)

    if not res:
        return None

    _, job_id = res

    data = r.hget(f"job:{job_id}", "data")

    if not data:
        return None

    return json.loads(data)


def ack_job(job_id):
    r.hset(f"job:{job_id}", "status", "done")
    print("[ACK]", job_id, flush=True)