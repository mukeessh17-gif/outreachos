import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from week4 import models
from week4.email_writer import generate_sequence, validate_email_sequence
from week4.schemas import EmailDraftInput, EmailSequenceInput, ResearchBrief


@pytest.fixture
def email_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(models.orgs.insert().values(id=1, name="Writer Org"))
        connection.execute(models.org_settings.insert().values(org_id=1))
        connection.execute(
            models.companies.insert().values(
                id=1,
                org_id=1,
                name="Fictional Widgets",
                employees=10,
            )
        )
    yield engine
    engine.dispose()


def _brief() -> ResearchBrief:
    return ResearchBrief(
        pain_points=["Manual product scheduling"],
        trigger="unknown",
        best_angle="Workflow automation for scheduling",
        confidence=0.8,
        sources=["https://public.example/about"],
    )


def _sequence() -> EmailSequenceInput:
    return EmailSequenceInput(
        emails=[
            EmailDraftInput(
                subject="A question about scheduling",
                body="I noticed manual product scheduling is a challenge. "
                "Would workflow automation be worth discussing?",
                send_delay_days=0,
            ),
            EmailDraftInput(
                subject="Following up on scheduling",
                body="Your brief mentions manual product scheduling. "
                "I can share a workflow automation idea if useful.",
                send_delay_days=3,
            ),
            EmailDraftInput(
                subject="Close the loop",
                body="If scheduling is not a priority, no reply is needed. "
                "I will close the loop here.",
                send_delay_days=7,
            ),
        ]
    )


def test_email_writer_rejects_banned_phrases() -> None:
    with pytest.raises(ValueError, match="banned"):
        validate_email_sequence(_sequence(), _brief(), "Fictional Widgets", ["worth discussing"])


def test_email_writer_rejects_unverified_numbers() -> None:
    unsafe = _sequence().model_copy(deep=True)
    unsafe.emails[0].body += " We save 90% of costs."
    with pytest.raises(ValueError, match="numeric claim"):
        validate_email_sequence(unsafe, _brief(), "Fictional Widgets", [])


def test_email_writer_uses_schema_and_token_budget(email_database) -> None:
    sequence = _sequence()

    def fake_generator(*_args, **_kwargs):
        return sequence, 400, 90

    result, input_tokens, output_tokens = generate_sequence(
        org_id=1,
        lead_id=1,
        company_name="Fictional Widgets",
        brief=_brief(),
        tone="friendly",
        sample_emails=[],
        banned_phrases=[],
        engine=email_database,
        generator=fake_generator,
    )
    assert len(result.emails) == 3
    assert (input_tokens, output_tokens) == (400, 90)
    with email_database.connect() as connection:
        usage = connection.execute(select(models.token_usage)).mappings().one()
    assert usage["input_tokens"] == 400
    assert usage["output_tokens"] == 90
