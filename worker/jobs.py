from app.supabase_client import supabase


def update(job_id, status, output_url=None):
    payload = {"status": status}

    if output_url:
        payload["output_url"] = output_url

    res = supabase.table("jobs") \
        .update(payload) \
        .eq("id", job_id) \
        .execute()

    return res


def get_job():
    try:
        res = supabase.rpc("get_next_job").execute()

        if not res.data:
            return None

        return res.data[0]

    except Exception as e:
        print("[JOB ERROR]", e)
        return None