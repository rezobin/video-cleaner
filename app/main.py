import uuid
import shutil
import os
import redis

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

r = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

GUEST_LIMIT = 2


def get_ip(request: Request):
    return request.client.host


def check_guest_limit(ip: str):
    key = f"guest:{ip}:uploads"
    count = r.get(key)
    return not (count and int(count) >= GUEST_LIMIT)


def incr_guest(ip: str):
    key = f"guest:{ip}:uploads"
    r.incr(key)
    r.expire(key, 60 * 60 * 24)


# -------------------------
# SAFE USER PARSING
# -------------------------
def safe_get_user(request: Request):
    try:
        return get_user(request.headers.get("authorization"))
    except:
        return None


# -------------------------
# UPLOAD
# -------------------------
@app.post("/upload")
def upload(
    request: Request,
    files: list[UploadFile] = File(...)
):
    ip = get_ip(request)
    user = safe_get_user(request)

    is_guest = user is None

    if is_guest and not check_guest_limit(ip):
        raise HTTPException(
            status_code=403,
            detail="GUEST_LIMIT_REACHED"
        )

    if is_guest:
        incr_guest(ip)

    job_id = str(uuid.uuid4())
    inputs = []

    try:
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

        return {"job_id": job_id}

    except Exception as e:
        print("[UPLOAD ERROR]", e)
        raise HTTPException(status_code=500, detail=str(e))
    request: Request,
    files: list[UploadFile] = File(...)
):
    ip = get_ip(request)
    user = safe_get_user(request)

    is_guest = user is None

    if is_guest and not check_guest_limit(ip):
        raise HTTPException(status_code=403, detail="Guest limit reached")

    if is_guest:
        incr_guest(ip)

    job_id = str(uuid.uuid4())
    inputs = []

    try:
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
            "job_id": job_id
        }

    except Exception as e:
        print("[UPLOAD ERROR]", e)
        raise HTTPException(status_code=500, detail=str(e))