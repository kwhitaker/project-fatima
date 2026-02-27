"""FastAPI auth dependency: validate Supabase JWT and return caller user_id."""

import os

import jwt
from fastapi import Header, HTTPException


def get_caller_id(authorization: str | None = Header(default=None)) -> str:
    """Validate Bearer JWT from Supabase and return the caller's user_id (sub claim).

    Raises 401 if the token is missing or invalid.
    Reads SUPABASE_JWT_SECRET from the environment for signature verification.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ")
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "")
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET not configured")

    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},  # Supabase JWTs use "authenticated" audience
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing sub claim")
    return str(sub)
