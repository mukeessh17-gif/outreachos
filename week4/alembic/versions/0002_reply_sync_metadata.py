"""Store Gmail message and thread IDs for idempotent reply synchronization."""

from alembic import op
from sqlalchemy import Column, Text, inspect

revision = "0002_reply_sync_metadata"
down_revision = "0001_org_scoped_application"
branch_labels = None
depends_on = None


def _add_column(table_name: str, column_name: str) -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}
    if column_name not in columns:
        op.add_column(table_name, Column(column_name, Text(), nullable=True))


def upgrade() -> None:
    _add_column("outbox", "thread_id")
    _add_column("replies", "sender_email")
    _add_column("replies", "source_message_id")
    _add_column("replies", "thread_id")
    unique_constraints = inspect(op.get_bind()).get_unique_constraints("replies")
    if not any(item.get("column_names") == ["org_id", "source_message_id"] for item in unique_constraints):
        op.create_unique_constraint(
            "uq_replies_org_source_message",
            "replies",
            ["org_id", "source_message_id"],
        )


def downgrade() -> None:
    raise RuntimeError("Reply sync metadata is retained to preserve inbox history.")
