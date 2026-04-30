import os
import uuid
import shutil

from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_user
from app.supabase_client import supabase

from queue import push_job  # 👈 AJOUT

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

print("[API] REDIS =", os.getenv("REDIS_URL"))

@app.post("/upload")
def upload(files: list[UploadFile] = File(...), user=Depends(get_user)):

    job_id = str(uuid.uuid4())

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

    # DB (tracking)
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user["sub"],
        "status": "queued",
        "input_paths": inputs
    }).execute()

    # 🔥 REDIS PUSH
    push_job({
        "id": job_id,
        "input_paths": inputs
    })

    print("[DEBUG] pushing job:", job_id)


    return {"job_id": job_id}