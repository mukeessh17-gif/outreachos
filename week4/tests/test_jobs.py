from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select, update
from sqlalchemy.pool import StaticPool

from week4 import models
from week4.job_queue import enqueue_job, process_one


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(models.orgs.insert().values(id=1, name="Job Org"))
        connection.execute(models.org_settings.insert().values(org_id=1))
        connection.execute(
            models.companies.insert(),
            [
                {"org_id": 1, "name": f"Fake Company {number}", "employees": 5}
                for number in range(200)
            ],
        )
    return engine


def test_two_hundred_leads_are_enqueued_and_processed_once() -> None:
    engine = _engine()
    processed: list[int] = []
    with engine.connect() as connection:
        lead_ids = connection.execute(select(models.companies.c.id)).scalars().all()
    for lead_id in lead_ids:
        first = enqueue_job(1, lead_id, "research", engine=engine)
        duplicate = enqueue_job(1, lead_id, "research", engine=engine)
        assert duplicate == first

    for _ in range(200):
        assert process_one(
            1,
            {"research": lambda job: processed.append(job["lead_id"])},
            engine=engine,
        ) == "done"
    assert process_one(1, {}, engine=engine) == "idle"
    assert len(processed) == 200
    assert len(set(processed)) == 200
    with engine.connect() as connection:
        done_count = connection.execute(
            select(models.jobs.c.id).where(models.jobs.c.status == "done")
        ).all()
    assert len(done_count) == 200
    engine.dispose()


def test_jobs_retry_then_become_dead_after_max_attempts() -> None:
    engine = _engine()
    with engine.begin() as connection:
        lead_id = connection.execute(select(models.companies.c.id).limit(1)).scalar_one()
    job_id = enqueue_job(1, lead_id, "research", engine=engine)
    with engine.begin() as connection:
        connection.execute(
            update(models.jobs)
            .where(models.jobs.c.id == job_id)
            .values(max_attempts=2)
        )
    now = datetime.now(timezone.utc)
    failing_handler = lambda _job: (_ for _ in ()).throw(RuntimeError("fixture failure"))
    assert process_one(1, {"research": failing_handler}, engine=engine, now=now) == "retry"
    assert process_one(
        1,
        {"research": failing_handler},
        engine=engine,
        now=now + timedelta(seconds=1),
    ) == "idle"
    with engine.begin() as connection:
        connection.execute(
            update(models.jobs)
            .where(models.jobs.c.id == job_id)
            .values(available_at=now)
        )
    assert process_one(
        1,
        {"research": failing_handler},
        engine=engine,
        now=now + timedelta(seconds=4),
    ) == "dead"
    with engine.connect() as connection:
        row = connection.execute(
            select(models.jobs.c.status, models.jobs.c.attempts).where(
                models.jobs.c.id == job_id
            )
        ).one()
    assert row == ("dead", 2)
    engine.dispose()
