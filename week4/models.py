"""SQLAlchemy Core schema for the tenant-scoped OutreachOS application."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)

metadata = MetaData()

orgs = Table(
    "orgs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("plan", String(20), nullable=False, server_default="free"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(320), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
memberships = Table(
    "memberships",
    metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String(20), nullable=False, server_default="member"),
    CheckConstraint("role IN ('owner', 'member')", name="ck_memberships_role"),
)

companies = Table(
    "companies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("name", Text, nullable=False),
    Column("city", Text),
    Column("employees", Integer, nullable=False, server_default="0"),
    Column("has_website", Boolean, nullable=False, server_default="false"),
    Column("website", Text),
    Column("pipeline_stage", String(20), nullable=False, server_default="new"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("org_id", "name", name="uq_companies_org_name"),
)
contacts = Table(
    "contacts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("company_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("full_name", Text, nullable=False, server_default=""),
    Column("email", Text, nullable=False),
    Column("role", Text),
    Column("status", String(20), nullable=False, server_default="new"),
    UniqueConstraint("company_id", "email", name="uq_contacts_company_email"),
)
lead_research = Table(
    "lead_research",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("company_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("summary", Text, nullable=False, server_default=""),
    Column("confidence", Float, nullable=False, server_default="0"),
    Column("pain_points", JSON, nullable=False, server_default="[]"),
    Column("trigger", Text, nullable=False, server_default="unknown"),
    Column("best_angle", Text, nullable=False, server_default="unknown"),
    Column("sources", JSON, nullable=False, server_default="[]"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

org_settings = Table(
    "org_settings",
    metadata,
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), primary_key=True),
    Column("tone", Text, nullable=False, server_default="professional"),
    Column("sample_emails", JSON, nullable=False, server_default="[]"),
    Column("banned_phrases", JSON, nullable=False, server_default="[]"),
    Column("sender_postal_address", Text, nullable=False, server_default=""),
    Column("calendar_link", Text, nullable=False, server_default=""),
    Column("daily_token_budget", Integer, nullable=False, server_default="100000"),
    Column("per_lead_token_budget", Integer, nullable=False, server_default="10000"),
    Column("daily_lead_limit", Integer, nullable=False, server_default="1000"),
)
llm_calls = Table(
    "llm_calls",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("purpose", String(60), nullable=False),
    Column("model", String(100), nullable=False),
    Column("input_tokens", Integer, nullable=False, server_default="0"),
    Column("output_tokens", Integer, nullable=False, server_default="0"),
    Column("latency_ms", Integer, nullable=False, server_default="0"),
    Column("success", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
token_usage = Table(
    "token_usage",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("lead_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("input_tokens", Integer, nullable=False, server_default="0"),
    Column("output_tokens", Integer, nullable=False, server_default="0"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

jobs = Table(
    "jobs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("lead_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("step", String(40), nullable=False),
    Column("payload", JSON, nullable=False, server_default="{}"),
    Column("status", String(20), nullable=False, server_default="pending"),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("max_attempts", Integer, nullable=False, server_default="5"),
    Column("available_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("locked_at", DateTime(timezone=True)),
    Column("last_error", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("org_id", "lead_id", "step", name="uq_jobs_org_lead_step"),
    CheckConstraint("status IN ('pending', 'running', 'done', 'dead')", name="ck_jobs_status"),
)
email_sequences = Table(
    "email_sequences",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("lead_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("status", String(20), nullable=False, server_default="draft"),
    Column("prompt_version", String(20), nullable=False, server_default="v1"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("status IN ('draft', 'approved', 'rejected')", name="ck_sequence_status"),
)
email_drafts = Table(
    "email_drafts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("sequence_id", ForeignKey("email_sequences.id", ondelete="CASCADE"), nullable=False),
    Column("position", Integer, nullable=False),
    Column("subject", Text, nullable=False),
    Column("body", Text, nullable=False),
    Column("send_delay_days", Integer, nullable=False, server_default="0"),
    Column("status", String(20), nullable=False, server_default="draft"),
)
inboxes = Table(
    "inboxes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("email", String(320), nullable=False),
    Column("encrypted_token", Text, nullable=False, server_default=""),
    Column("daily_limit", Integer, nullable=False, server_default="30"),
    UniqueConstraint("org_id", "email", name="uq_inboxes_org_email"),
)
outbox = Table(
    "outbox",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("lead_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("draft_id", ForeignKey("email_drafts.id", ondelete="CASCADE")),
    Column("inbox_id", ForeignKey("inboxes.id", ondelete="SET NULL")),
    Column("recipient", String(320), nullable=False),
    Column("subject", Text, nullable=False),
    Column("body", Text, nullable=False),
    Column("status", String(20), nullable=False, server_default="dry_run"),
    Column("message_id", Text),
    Column("thread_id", Text),
    Column("scheduled_at", DateTime(timezone=True)),
    Column("locked_at", DateTime(timezone=True)),
    Column("sent_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("org_id", "draft_id", name="uq_outbox_org_draft"),
)
suppression_list = Table(
    "suppression_list",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("email", String(320), nullable=False),
    Column("reason", String(40), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("org_id", "email", name="uq_suppression_org_email"),
)
replies = Table(
    "replies",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("lead_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("sender_email", String(320)),
    Column("source_message_id", Text),
    Column("thread_id", Text),
    Column("body", Text, nullable=False),
    Column("category", String(30), nullable=False),
    Column("draft_response", Text),
    Column("status", String(20), nullable=False, server_default="draft"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("org_id", "source_message_id", name="uq_replies_org_source_message"),
)
pipeline_events = Table(
    "pipeline_events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("lead_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("stage", String(20), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
prompt_experiments = Table(
    "prompt_experiments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("lead_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("version", String(20), nullable=False),
    Column("outcome", String(30), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
bookings = Table(
    "bookings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("lead_id", ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
    Column("calendar_event_id", Text),
    Column("starts_at", DateTime(timezone=True), nullable=False),
    Column("ends_at", DateTime(timezone=True), nullable=False),
    Column("status", String(20), nullable=False, server_default="requested"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
stripe_subscriptions = Table(
    "stripe_subscriptions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
    Column("customer_id", String(255)),
    Column("subscription_id", String(255)),
    Column("price_id", String(255)),
    Column("status", String(30), nullable=False, server_default="inactive"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
stripe_events = Table(
    "stripe_events",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("event_type", String(100), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
feedback = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("rating", Integer, nullable=False),
    Column("message", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating"),
)
oauth_states = Table(
    "oauth_states",
    metadata,
    Column("org_id", ForeignKey("orgs.id", ondelete="CASCADE"), primary_key=True),
    Column("nonce", String(100), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)

Index("ix_jobs_ready", jobs.c.status, jobs.c.available_at)
Index("ix_outbox_daily", outbox.c.org_id, outbox.c.inbox_id, outbox.c.created_at)
Index("ix_token_usage_day", token_usage.c.org_id, token_usage.c.lead_id, token_usage.c.created_at)
