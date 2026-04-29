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


def get_job():
    try:
        res = supabase.rpc("get_next_job").execute()

        if not res.data:
            return None

        job = res.data[0]

        print("[JOBS] Picked job:", job["id"])

        return job

    except Exception as e:
        print("[JOBS ERROR]:", e)
        return None