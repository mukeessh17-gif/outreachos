from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from week4 import models
from week4.seed_demo import seed_demo_data


def test_seed_demo_data_is_fictional_scoped_and_idempotent() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(models.orgs.insert().values(id=1, name="Demo Org"))
        connection.execute(models.org_settings.insert().values(org_id=1))
        connection.execute(models.orgs.insert().values(id=2, name="Other Org"))
        connection.execute(models.org_settings.insert().values(org_id=2))

    assert seed_demo_data(1, engine=engine) == 30
    assert seed_demo_data(1, engine=engine) == 0
    with engine.begin() as connection:
        leads = connection.execute(
            select(models.companies.c.name).where(models.companies.c.org_id == 1)
        ).scalars().all()
        research = connection.execute(
            select(models.lead_research.c.sources).where(models.lead_research.c.org_id == 1)
        ).scalars().all()
        other_org_leads = connection.execute(
            select(models.companies.c.id).where(models.companies.c.org_id == 2)
        ).all()
    assert len(leads) == len(research) == 30
    assert all(name.startswith("Fictional ") for name in leads)
    assert all(source == ["https://fictional.example/demo"] for source in research)
    assert other_org_leads == []
    engine.dispose()
