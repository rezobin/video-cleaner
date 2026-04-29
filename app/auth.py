import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException

from app.config import JWKS_URL, SUPABASE_JWT_AUD

def get_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401)

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
        raise HTTPException(401)