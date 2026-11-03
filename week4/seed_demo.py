"""Seed a selected workspace with idempotent fictional company research data."""

import argparse

from sqlalchemy import select
from sqlalchemy.engine import Engine

from week2.db import get_engine
from week4 import models
from week4.db import tenant_transaction

_pain_points = (
    "Manual production scheduling",
    "Slow inventory reconciliation",
    "Disconnected maintenance records",
    "Repeated warehouse data entry",
    "Unclear supplier handoffs",
)
_stages = ("new", "contacted", "replied", "meeting", "closed")


def seed_demo_data(org_id: int, *, engine: Engine | None = None) -> int:
    database = engine or get_engine()
    inserted_count = 0
    with tenant_transaction(org_id, engine=database) as connection:
        organization = connection.execute(
            select(models.orgs.c.id).where(models.orgs.c.id == org_id)
        ).first()
        if organization is None:
            raise ValueError(f"Organization {org_id} was not found.")
        for index in range(30):
            number = index + 1
            name = f"Fictional Operations Company {number:02}"
            lead_id = connection.execute(
                select(models.companies.c.id).where(
                    models.companies.c.org_id == org_id,
                    models.companies.c.name == name,
                )
            ).scalar_one_or_none()
            if lead_id is None:
                lead_id = connection.execute(
                    models.companies.insert()
                    .values(
                        org_id=org_id,
                        name=name,
                        city=("Coimbatore" if number % 2 else "Pune"),
                        employees=10 + number,
                        has_website=False,
                        pipeline_stage=_stages[index % len(_stages)],
                    )
                    .returning(models.companies.c.id)
                ).scalar_one()
                inserted_count += 1
            research_exists = connection.execute(
                select(models.lead_research.c.id).where(
                    models.lead_research.c.org_id == org_id,
                    models.lead_research.c.company_id == lead_id,
                )
            ).first()
            if research_exists is None:
                pain = _pain_points[index % len(_pain_points)]
                connection.execute(
                    models.lead_research.insert().values(
                        org_id=org_id,
                        company_id=lead_id,
                        summary="Fictional demonstration data; not a claim about a real business.",
                        confidence=0.5,
                        pain_points=[pain],
                        trigger="unknown",
                        best_angle=f"Explore {pain.lower()} as a hypothetical workflow.",
                        sources=["https://fictional.example/demo"],
                    )
                )
    return inserted_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org-id", type=int, required=True)
    args = parser.parse_args()
    count = seed_demo_data(args.org_id)
    print(f"Added {count} fictional demo leads. Existing demo leads were preserved.")


if __name__ == "__main__":
    main()
