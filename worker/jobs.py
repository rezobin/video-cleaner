from app.supabase_client import supabase


from app.supabase_client import supabase

def update(job_id: str, status: str, output_url: str = None):
    payload = {
        "status": status
    }

    if output_url:
        payload["output_url"] = output_url

    res = supabase.table("jobs").update(payload).eq("id", job_id).execute()

    print(f"[JOBS UPDATE] {job_id} -> {payload}")
    return res