import asyncio
import uuid
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _jwk_client() -> PyJWKClient:
    # Supabase Auth signs JWTs with the project's JWT signing keys —
    # asymmetric (e.g. ES256), not a shared secret — verified against the
    # public keys published at this JWKS endpoint. PyJWKClient fetches and
    # caches them in-process.
    return PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> uuid.UUID:
    """Verify a Supabase-issued JWT and return the authenticated user's id."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )

    try:
        # get_signing_key_from_jwt does a blocking HTTP fetch on a JWKS
        # cache miss — offload it so it doesn't block the event loop.
        signing_key = await asyncio.to_thread(
            _jwk_client().get_signing_key_from_jwt, credentials.credentials
        )
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    sub = payload.get("sub")
    try:
        return uuid.UUID(sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing valid subject"
        )
