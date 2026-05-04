import uuid
import shutil

from fastapi import FastAPI, UploadFile, File, Depends
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

print("=== API BOOTED VERSION X ===", flush=True)


@app.post("/upload")
def upload(files: list[UploadFile] = File(...), user=Depends(get_user)):
    print("=== UPLOAD START ===", flush=True)

    try:
        job_id = str(uuid.uuid4())
        inputs = []

        for i, f in enumerate(files):
            print("[UPLOAD] processing file", i, flush=True)

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

        print("[UPLOAD] files uploaded", flush=True)

        supabase.table("jobs").insert({
            "id": job_id,
            "user_id": user["sub"],
            "status": "queued",
            "input_paths": inputs
        }).execute()

        print("[UPLOAD] DB insert OK", flush=True)

        push_job({
            "id": job_id,
            "input_paths": inputs
        })

        print("[UPLOAD] PUSH DONE", flush=True)

        return {"job_id": job_id}

    except Exception as e:
        print("[UPLOAD ERROR]", repr(e), flush=True)
        return {"error": str(e)}

@app.get("/ping")
def ping():
    print("PING HIT", flush=True)
    return {"status": "ok"}