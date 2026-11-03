"""Database transaction helpers for row-level security and tenant scope."""

from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import Connection, text
from sqlalchemy.engine import Engine

from week2.db import get_engine


@contextmanager
def tenant_transaction(
    org_id: int,
    user_id: int | None = None,
    engine: Engine | None = None,
) -> Iterator[Connection]:
    """Set transaction-local Postgres policies before tenant queries run."""
    selected_engine = engine or get_engine()
    with selected_engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": str(org_id)},
            )
            if user_id is not None:
                connection.execute(
                    text("SELECT set_config('app.current_user_id', :user_id, true)"),
                    {"user_id": str(user_id)},
                )
        yield connection


def set_rls_context(connection: Connection, org_id: int, user_id: int | None = None) -> None:
    """Configure an existing transaction before RLS-protected reads or writes."""
    if connection.dialect.name != "postgresql":
        return
    connection.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"),
        {"org_id": str(org_id)},
    )
    if user_id is not None:
        connection.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": str(user_id)},
        )
