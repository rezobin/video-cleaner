import uuid
import shutil

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_user
from app.supabase_client import supabase

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# HEALTHCHECK
# -------------------------

@app.get("/")
def root():
    return {"status": "ok"}

# -------------------------
# UPLOAD
# -------------------------

@app.post("/upload")
def upload(files: list[UploadFile] = File(...), user=Depends(get_user)):

    job_id = str(uuid.uuid4())

    print("[UPLOAD] job created:", job_id)

    inputs = []

    for i, f in enumerate(files):

        path = f"{job_id}/{i}.mp4"
        temp_path = f"/tmp/{job_id}_{i}.mp4"

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)

        supabase.storage.from_("videos").upload(
            path=path,
            file=open(temp_path, "rb"),
            file_options={"content-type": "video/mp4", "upsert": "true"}
        )

        inputs.append(path)

    res = supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user["sub"],
        "status": "queued"
        "input_paths": inputs
    }).execute()

    print("[UPLOAD] DB insert response:", res)

    return {"job_id": job_id}

# -------------------------
# STATUS
# -------------------------

@app.get("/status/{job_id}")
def status(job_id: str):

    res = supabase.table("jobs").select("*").eq("id", job_id).single().execute()

    if not res.data:
        raise HTTPException(404, "Job not found")

    return {
        "status": res.data["status"],
        "job_id": res.data["id"]
    }


# -------------------------
# DOWNLOAD (IMPORTANT MANQUANT)
# -------------------------

@app.get("/download/{job_id}")
def download(job_id: str, user=Depends(get_user)):

    res = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    job = res.data

    if not job:
        raise HTTPException(404)

    if job["user_id"] != user["sub"]:
        raise HTTPException(403)

    return {
        "output_url": job.get("output_url"),
        "status": job["status"]
    }