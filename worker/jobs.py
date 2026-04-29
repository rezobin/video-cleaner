from app.supabase_client import supabase

def update(job_id, status, output_url=None):

    payload = {
        "status": status
    }

    if output_url is not None:
        payload["output_url"] = output_url

    res = supabase.table("jobs") \
        .update(payload) \
        .eq("id", job_id) \
        .execute()

    print("[JOBS UPDATE]", job_id, "->", payload)
    print("[JOBS UPDATE RESPONSE]", res)

    return res