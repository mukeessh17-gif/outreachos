"""Add organizations, auth, and tenant-scoped application tables."""

from alembic import op
from sqlalchemy import Column, DateTime, inspect, text

from week4 import models

revision = "0001_org_scoped_application"
down_revision = None
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _add_org_id_and_backfill(table_name: str, join_sql: str | None = None) -> None:
    bind = op.get_bind()
    if "org_id" not in _columns(table_name):
        op.execute(text(f"ALTER TABLE {table_name} ADD COLUMN org_id INTEGER"))
    if join_sql:
        op.execute(text(join_sql))
    op.execute(text(f"UPDATE {table_name} SET org_id = 1 WHERE org_id IS NULL"))
    op.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN org_id SET NOT NULL"))
    constraints = inspect(bind).get_foreign_keys(table_name)
    if not any(item.get("constrained_columns") == ["org_id"] for item in constraints):
        op.create_foreign_key(
            f"fk_{table_name}_org_id",
            table_name,
            "orgs",
            ["org_id"],
            ["id"],
            ondelete="CASCADE",
        )


def _add_column_if_missing(table_name: str, column_sql: str, column_name: str) -> None:
    if column_name not in _columns(table_name):
        op.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))


def upgrade() -> None:
    bind = op.get_bind()
    models.orgs.create(bind, checkfirst=True)
    models.users.create(bind, checkfirst=True)
    models.memberships.create(bind, checkfirst=True)
    bind.execute(
        text(
            "INSERT INTO orgs (id, name, plan) VALUES (1, 'Migrated Leads', 'free') "
            "ON CONFLICT (id) DO NOTHING"
        )
    )

    tables = set(inspect(bind).get_table_names())
    if "companies" not in tables:
        models.companies.create(bind)
    else:
        _add_org_id_and_backfill("companies")
        _add_column_if_missing("companies", "website TEXT", "website")
        _add_column_if_missing(
            "companies",
            "pipeline_stage VARCHAR(20) NOT NULL DEFAULT 'new'",
            "pipeline_stage",
        )
        op.execute(text("UPDATE companies SET employees = 0 WHERE employees IS NULL"))
        op.execute(text("ALTER TABLE companies ALTER COLUMN employees SET NOT NULL"))

    tables = set(inspect(bind).get_table_names())
    if "contacts" not in tables:
        models.contacts.create(bind)
    else:
        _add_org_id_and_backfill(
            "contacts",
            "UPDATE contacts AS c SET org_id = co.org_id "
            "FROM companies AS co WHERE c.company_id = co.id AND c.org_id IS NULL",
        )
        _add_column_if_missing("contacts", "VARCHAR(20) NOT NULL DEFAULT 'new'", "status")

    tables = set(inspect(bind).get_table_names())
    if "lead_research" not in tables:
        models.lead_research.create(bind)
    else:
        _add_org_id_and_backfill(
            "lead_research",
            "UPDATE lead_research AS r SET org_id = co.org_id "
            "FROM companies AS co WHERE r.company_id = co.id AND r.org_id IS NULL",
        )
        op.execute(
            text(
                "ALTER TABLE lead_research ALTER COLUMN confidence TYPE DOUBLE PRECISION "
                "USING confidence::double precision / 100.0"
            )
        )
        _add_column_if_missing("lead_research", "JSON NOT NULL DEFAULT '[]'", "pain_points")
        _add_column_if_missing("lead_research", "TEXT NOT NULL DEFAULT 'unknown'", "trigger")
        _add_column_if_missing("lead_research", "TEXT NOT NULL DEFAULT 'unknown'", "best_angle")
        _add_column_if_missing("lead_research", "JSON NOT NULL DEFAULT '[]'", "sources")

    for constraint in inspect(bind).get_unique_constraints("companies"):
        if constraint.get("column_names") == ["name"]:
            op.drop_constraint(constraint["name"], "companies", type_="unique")
    if not any(
        item.get("column_names") == ["org_id", "name"]
        for item in inspect(bind).get_unique_constraints("companies")
    ):
        op.create_unique_constraint("uq_companies_org_name", "companies", ["org_id", "name"])

    models.metadata.create_all(bind=bind, checkfirst=True)
    if "locked_at" not in _columns("jobs"):
        op.add_column("jobs", Column("locked_at", DateTime(timezone=True), nullable=True))
    _add_column_if_missing("replies", "VARCHAR(320)", "sender_email")

    if bind.dialect.name == "postgresql":
        for table_name, table in models.metadata.tables.items():
            if "org_id" not in table.c:
                continue
            policy = f"tenant_isolation_{table_name}"
            op.execute(text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
            op.execute(text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
            op.execute(text(f'DROP POLICY IF EXISTS "{policy}" ON "{table_name}"'))
            if table_name == "memberships":
                predicate = (
                    "org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer "
                    "OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer"
                )
            else:
                predicate = (
                    "org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer"
                )
            op.execute(
                text(
                    f'CREATE POLICY "{policy}" ON "{table_name}" '
                    f"USING ({predicate}) WITH CHECK ({predicate})"
                )
            )
        op.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('orgs', 'id'), "
                "GREATEST((SELECT MAX(id) FROM orgs), 1))"
            )
        )


def downgrade() -> None:
    raise RuntimeError(
        "This tenant migration is intentionally irreversible because it preserves and scopes existing customer data."
    )
