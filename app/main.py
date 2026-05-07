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

import stripe
from fastapi.responses import JSONResponse

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

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
FREE_USER_LIMIT = 5
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


    # -------------------------
    # FREE USER LIMIT
    # -------------------------
    if user:

        db_user = supabase.table("users") \
            .select("plan, upload_count") \
            .eq("id", user["sub"]) \
            .single() \
            .execute()

        db_user = db_user.data

        is_premium = db_user.get("plan") == "monthly"

        if not is_premium:

            uploads = db_user.get("upload_count", 0)

            if uploads >= FREE_USER_LIMIT:
                raise HTTPException(
                    status_code=403,
                    detail="PAYWALL_REQUIRED"
                )

            supabase.table("users") \
                .update({
                    "upload_count": uploads + 1
                }) \
                .eq("id", user["sub"]) \
                .execute()




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



@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):

    user = get_user_optional(request)

    if not user:
        raise HTTPException(status_code=401)

    session = stripe.checkout.Session.create(

        payment_method_types=["card"],

        mode="subscription",

        line_items=[{
            "price": os.getenv("STRIPE_MONTHLY_PRICE_ID"),
            "quantity": 1
        }],

        success_url=f"{os.getenv('FRONTEND_URL')}?success=true",

        cancel_url=f"{os.getenv('FRONTEND_URL')}?canceled=true",

        customer_email=user["email"],

        client_reference_id=user["sub"]
    )

    return JSONResponse({
        "url": session.url
    })


# -------------------------
# STRIPE WEBHOOK
# -------------------------

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):

    payload = await request.body()

    sig_header = request.headers.get("stripe-signature")

    event = stripe.Webhook.construct_event(
        payload,
        sig_header,
        os.getenv("STRIPE_WEBHOOK_SECRET")
    )

    # -------------------------
    # PAYMENT SUCCESS
    # -------------------------
    if event["type"] == "checkout.session.completed":

        session_data = event["data"]["object"]

        user_id = session_data["client_reference_id"]

        customer_id = session_data["customer"]

        subscription_id = session_data["subscription"]

        supabase.table("users") \
            .update({
                "plan": "monthly",
                "subscription_status": "active",
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id
            }) \
            .eq("id", user_id) \
            .execute()

    return {"ok": True}