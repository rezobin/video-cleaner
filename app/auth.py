import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException, Request

from app.supabase_client import supabase
from app.config import JWKS_URL, SUPABASE_JWT_AUD


# -------------------------
# STRICT (protected routes)
# -------------------------
def get_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing auth header")

    token = authorization.replace("Bearer ", "")

    try:
        jwk_client = PyJWKClient(JWKS_URL)
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience=SUPABASE_JWT_AUD
        )

        return payload

    except Exception as e:
        print("AUTH ERROR:", e)
        raise HTTPException(status_code=401, detail="Invalid token")


# -------------------------
# OPTIONAL (guest allowed)
# -------------------------
def get_user_optional(authorization: str = Header(None)):
    if not authorization:
        return None

    try:
        return get_user(authorization)
    except:
        return None


# -------------------------
# UPSERT USER (safe)
# -------------------------
def ensure_user(user):
    if not user:
        return

    try:
        existing = supabase.table("users") \
            .select("id") \
            .eq("id", user["sub"]) \
            .execute()

        if not existing.data:
            supabase.table("users").insert({
                "id": user["sub"],
                "email": user.get("email")
            }).execute()

    except Exception as e:
        print("[ENSURE USER ERROR]", e)