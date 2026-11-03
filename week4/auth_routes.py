"""Public signup/login routes and the authenticated account endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from week2.db import get_engine
from week4.auth import (
    CurrentOrg,
    CurrentIdentity,
    check_rate_limit,
    create_access_token,
    get_client_ip,
    hash_password,
    verify_password,
)
from week4.schemas import LoginRequest, SignupRequest, TokenResponse
from week4.db import set_rls_context

router = APIRouter(prefix="/auth", tags=["auth"])


def rate_limit_auth(request: Request) -> None:
    check_rate_limit(get_client_ip(request))


AuthRateLimit = Annotated[None, Depends(rate_limit_auth)]


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, _rate_limit: AuthRateLimit) -> dict[str, object]:
    engine = get_engine()
    try:
        with engine.begin() as connection:
            organization = connection.execute(
                text("INSERT INTO orgs (name) VALUES (:name) RETURNING id, name"),
                {"name": payload.org_name.strip()},
            ).mappings().one()
            user = connection.execute(
                text(
                    "INSERT INTO users (email, password_hash) "
                    "VALUES (:email, :password_hash) RETURNING id"
                ),
                {"email": payload.email, "password_hash": hash_password(payload.password)},
            ).mappings().one()
            set_rls_context(connection, organization["id"], user["id"])
            connection.execute(
                text(
                    "INSERT INTO memberships (user_id, org_id, role) "
                    "VALUES (:user_id, :org_id, 'owner')"
                ),
                {"user_id": user["id"], "org_id": organization["id"]},
            )
            connection.execute(
                text("INSERT INTO org_settings (org_id) VALUES (:org_id)"),
                {"org_id": organization["id"]},
            )
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error

    return {
        "access_token": create_access_token(user["id"], organization["id"]),
        "org_id": organization["id"],
        "org_name": organization["name"],
        "user_id": user["id"],
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, _rate_limit: AuthRateLimit) -> dict[str, object]:
    with get_engine().connect() as connection:
        row = connection.execute(
            text(
                "SELECT id AS user_id, password_hash FROM users WHERE email = :email"
            ),
            {"email": payload.email},
        ).mappings().first()
    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    with get_engine().begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": str(row["user_id"])},
            )
        membership = connection.execute(
            text(
                "SELECT m.org_id, o.name AS org_name FROM memberships m "
                "JOIN orgs o ON o.id = m.org_id "
                "WHERE m.user_id = :user_id ORDER BY m.org_id LIMIT 1"
            ),
            {"user_id": row["user_id"]},
        ).mappings().first()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not belong to an organization.",
        )
    return {
        "access_token": create_access_token(row["user_id"], membership["org_id"]),
        "org_id": membership["org_id"],
        "org_name": membership["org_name"],
        "user_id": row["user_id"],
    }


@router.get("/me")
def get_me(identity: CurrentIdentity) -> dict[str, object]:
    return identity
