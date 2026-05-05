import uuid
import shutil
import os
import redis

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_user, ensure_user, get_user_optional
from app.supabase_client import supabase
from app.job_queue import push_job
from app.auth import ensure_user

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://video-cleaner-ixce.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


r = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

GUEST_LIMIT = 2
USER_LIMIT = 50


# -------------------------
# IP
# -------------------------
def get_ip(request: Request):
    return request.client.host


# -------------------------
# GUEST LIMIT
# -------------------------
def check_guest_limit(ip: str):
    key = f"guest:{ip}:uploads"
    count = r.get(key)
    return not (count and int(count) >= GUEST_LIMIT)


def incr_guest(ip: str):
    key = f"guest:{ip}:uploads"
    r.incr(key)
    r.expire(key, 60 * 60 * 24)


# -------------------------
# SAFE AUTH (CRITICAL FIX)
# -------------------------
def safe_get_user(request: Request):
    auth = request.headers.get("authorization")

    if not auth:
        return None

    try:
        user = get_user(auth)
        ensure_user(user)
        return user
    except:
        return None


def increment_user_upload(user_id: str):
    try:
        supabase.rpc("increment_uploads", {"user_id": user_id}).execute()
    except Exception as e:
        print("[UPLOAD COUNT ERROR]", e)


# -------------------------
# UPLOAD
# -------------------------
@app.post("/upload")
def upload(request: Request, files: list[UploadFile] = File(...)):
    ip = get_ip(request)
    user = get_user_optional(request)

    is_guest = user is None

    # -------------------------
    # LIMITING
    # -------------------------
    if is_guest:
        if not check_guest_limit(ip):
            raise HTTPException(
                status_code=403,
                detail="GUEST_LIMIT_REACHED"
            )
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

        return {"job_id": job_id, "guest": is_guest}

    except Exception as e:
        print("[UPLOAD ERROR]", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
def status(job_id: str):
    data = r.hgetall(f"job:{job_id}")

    if not data:
        return {
            "status": "unknown",
            "progress": 0
        }

    return {
        "status": data.get("status", "queued"),
        "progress": int(data.get("progress", 0)),
        "output_url": data.get("output_url")
    }