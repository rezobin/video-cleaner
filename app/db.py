from app.supabase_client import supabase


def update_job(job_id, status, output_url=None):

    payload = {"status": status}

    if output_url:
        payload["output_url"] = output_url

    supabase.table("jobs") \
        .update(payload) \
        .eq("id", job_id) \
        .execute()