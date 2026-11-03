"""Add scheduling and claim metadata to outbox entries."""

from alembic import op
from sqlalchemy import Column, DateTime, inspect

revision = "0003_scheduled_outbox"
down_revision = "0002_reply_sync_metadata"
branch_labels = None
depends_on = None


def _add_column(column_name: str) -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("outbox")}
    if column_name not in columns:
        op.add_column("outbox", Column(column_name, DateTime(timezone=True), nullable=True))


def upgrade() -> None:
    _add_column("scheduled_at")
    _add_column("locked_at")
    _add_column("sent_at")


def downgrade() -> None:
    raise RuntimeError("Outbox schedule metadata is retained to preserve delivery history.")
