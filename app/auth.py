import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException

from app.supabase_client import supabase

from app.config import JWKS_URL, SUPABASE_JWT_AUD


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
    
def ensure_user(user):
    try:
        existing = supabase.table("users").select("*").eq("id", user["sub"]).execute()

        if not existing.data:
            supabase.table("users").insert({
                "id": user["sub"],
                "email": user.get("email")
            }).execute()

    except Exception as e:
        print("[ENSURE USER ERROR]", e)


def get_user_optional(request: Request):
    try:
        from app.auth import get_user
        auth = request.headers.get("authorization")
        if not auth:
            return None
        return get_user(auth)
    except:
        return None