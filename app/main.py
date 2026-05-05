import uuid
import shutil
import time
import redis
import os

from fastapi import FastAPI, UploadFile, File, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_user
from app.supabase_client import supabase
from app.job_queue import push_job

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# REDIS (guest tracking)
# -------------------------
r = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)


GUEST_LIMIT = 2


def get_ip(request: Request):
    return request.client.host


def check_guest_limit(ip: str):
    key = f"guest:{ip}:uploads"
    count = r.get(key)

    if count and int(count) >= GUEST_LIMIT:
        return False

    return True


def incr_guest(ip: str):
    key = f"guest:{ip}:uploads"
    r.incr(key)
    r.expire(key, 60 * 60 * 24)  # 24h window


# -------------------------
# UPLOAD
# -------------------------
@app.post("/upload")
def upload(
    request: Request,
    files: list[UploadFile] = File(...),
    user=Depends(get_user)
):
    print("=== UPLOAD START ===", flush=True)

    ip = get_ip(request)

    is_guest = not user or "sub" not in user

    if is_guest:
        if not check_guest_limit(ip):
            raise HTTPException(status_code=403, detail="Guest limit reached (2 uploads/day)")
        incr_guest(ip)

    try:
        job_id = str(uuid.uuid4())
        inputs = []

        for i, f in enumerate(files):
            path = f"{job_id}/{i}.mp4"
            temp_path = f"/tmp/{job_id}_{i}.mp4"

            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)

            with open(temp_path, "rb") as file_data:
                supabase.storage.from_("videos").upload(
                    path=path,
                    file=file_data,
                    file_options={"content-type": "video/mp4", "upsert": "true"}
                )

            inputs.append(path)

        supabase.table("jobs").insert({
            "id": job_id,
            "user_id": user["sub"] if user else None,
            "status": "queued",
            "progress": 0,
            "input_paths": inputs
        }).execute()

        push_job({
            "id": job_id,
            "input_paths": inputs
        })

        return {
            "job_id": job_id,
            "guest": is_guest
        }

    except Exception as e:
        print("[UPLOAD ERROR]", repr(e), flush=True)
        return {"error": str(e)}