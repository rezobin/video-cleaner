import uuid
import shutil

from fastapi import FastAPI, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_user, ensure_user
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
# OPTIONAL AUTH (guest ok)
# -------------------------
def optional_user(authorization: str = Header(None)):
    if not authorization:
        return None

    try:
        return get_user(authorization)
    except:
        return None


# -------------------------
# UPLOAD
# -------------------------
@app.post("/upload")
def upload(files: list[UploadFile] = File(...), authorization: str = Header(None)):

    user = optional_user(authorization)

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

        # user tracking
        if user:
            ensure_user(user)

            supabase.rpc("increment_uploads", {
                "user_id": user["sub"]
            }).execute()

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
        print("[UPLOAD ERROR]", repr(e), flush=True)
        return {"error": str(e)}


# -------------------------
# STATUS
# -------------------------
from app.job_queue import r

@app.get("/status/{job_id}")
def status(job_id: str):

    db = supabase.table("jobs").select("*").eq("id", job_id).execute()

    if not db.data:
        return {"status": "not_found", "progress": 0}

    job = db.data[0]

    redis_data = r.hgetall(f"job:{job_id}")

    return {
        "status": redis_data.get("status") or job.get("status"),
        "progress": int(redis_data.get("progress") or job.get("progress") or 0),
        "output_url": redis_data.get("url") or job.get("output_url")
    }