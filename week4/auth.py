"""Authentication helpers and tenant-scoping dependencies."""

import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from week2.db import get_engine
from week4.db import set_rls_context

load_dotenv()

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
password_hasher = PasswordHasher()
bearer_scheme = HTTPBearer(auto_error=False)
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempts_lock = threading.Lock()


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET must be set in .env before auth is used.")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters.")
    return secret


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, org_id: int) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "org_id": org_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(claims, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def check_rate_limit(
    client_ip: str,
    max_attempts: int = 5,
    window_seconds: int = 60,
) -> None:
    """Keep auth attempt tracking bounded and safe across concurrent requests."""
    now = time.monotonic()
    with _attempts_lock:
        attempts = _attempts[client_ip]
        while attempts and now - attempts[0] >= window_seconds:
            attempts.popleft()
        if len(attempts) >= max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts. Try again later.",
                headers={"Retry-After": str(window_seconds)},
            )
        attempts.append(now)
        if len(_attempts) > 10_000:
            stale = [ip for ip, values in _attempts.items() if not values]
            for ip in stale:
                _attempts.pop(ip, None)


def get_client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host


def get_current_identity(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> dict[str, int | str]:
    """Authenticate the user and confirm their token's org membership."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = decode_access_token(credentials.credentials)
    try:
        user_id = int(claims["sub"])
        org_id = int(claims["org_id"])
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is missing required claims.",
        ) from error

    with get_engine().begin() as connection:
        set_rls_context(connection, org_id, user_id)
        membership = connection.execute(
            text(
                "SELECT m.role, o.name AS org_name FROM memberships m "
                "JOIN orgs o ON o.id = m.org_id "
                "WHERE m.user_id = :user_id AND m.org_id = :org_id"
            ),
            {"user_id": user_id, "org_id": org_id},
        ).mappings().first()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account is not a member of the requested organization.",
        )
    return {
        "org_id": org_id,
        "user_id": user_id,
        "role": membership["role"],
        "org_name": membership["org_name"],
    }


def get_current_org(
    identity: Annotated[dict[str, int | str], Depends(get_current_identity)],
) -> int:
    return int(identity["org_id"])


CurrentOrg = Annotated[int, Depends(get_current_org)]
CurrentIdentity = Annotated[dict[str, int | str], Depends(get_current_identity)]
