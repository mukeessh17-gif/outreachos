"""Compare prompt versions against the fake lead set and save a JSON report."""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from week4.email_writer import generate_sequence, validate_email_sequence
from week4.evals.golden_set import build_golden_set
from week4.schemas import EmailDraftInput, EmailSequenceInput, ResearchBrief
from week2.db import get_engine
from week4 import models

REPORTS_DIR = Path(__file__).parent / "reports"


def _offline_sequence(
    lead: dict[str, object],
    brief: ResearchBrief,
    version: str,
) -> EmailSequenceInput:
    if version == "v1":
        first_body = "Would a simpler workflow be useful for your team? I can share a short idea."
    else:
        first_body = (
            f"Your public brief mentions {brief.pain_points[0]}. "
            f"Would {brief.best_angle.lower()} be relevant to your team?"
        )
    name = str(lead["name"])
    return EmailSequenceInput(
        emails=[
            EmailDraftInput(
                subject=f"A workflow question for {name}" if version == "v2" else "A workflow question",
                body=first_body,
                send_delay_days=0,
            ),
            EmailDraftInput(
                subject="A second thought",
                body=f"If {brief.pain_points[0].lower()} is not a priority, no reply is needed.",
                send_delay_days=3,
            ),
            EmailDraftInput(
                subject="Close the loop",
                body="I will close the loop here, and you do not need to reply unless this is useful.",
                send_delay_days=7,
            ),
        ]
    )


def score_sequence(
    sequence: EmailSequenceInput,
    company_name: str,
    brief: ResearchBrief,
) -> dict[str, int]:
    all_text = " ".join(
        [email.subject + " " + email.body for email in sequence.emails]
    ).casefold()
    personalized = company_name.casefold() in all_text and any(
        point.casefold() in all_text for point in brief.pain_points
    )
    try:
        validate_email_sequence(sequence, brief, company_name, [])
        faithful = True
    except ValueError:
        faithful = False
    no_invented_facts = faithful and not re.search(
        r"\b\d+(?:\.\d+)?\s*(?:%|percent|customers|weeks|days)\b",
        all_text,
    )
    bodies_in_range = all(
        12 <= len(email.body.split()) <= 180 and len(email.body) <= 1_200
        for email in sequence.emails
    )
    return {
        "personalization": 5 if personalized else 1,
        "faithfulness": 5 if faithful else 0,
        "no_invented_facts": 5 if no_invented_facts else 0,
        "length": 5 if bodies_in_range else 2,
    }


def _live_generator(
    lead: dict[str, object],
    version: str,
    org_id: int,
    database_lead_id: int,
) -> EmailSequenceInput:
    brief = lead["brief"]
    if not isinstance(brief, ResearchBrief):
        raise TypeError("Golden lead brief has an invalid type.")
    sequence, _, _ = generate_sequence(
        org_id=org_id,
        lead_id=database_lead_id,
        company_name=str(lead["name"]),
        brief=brief,
        tone="clear, respectful, concise",
        sample_emails=[],
        banned_phrases=[],
        prompt_version=version,
    )
    return sequence


def run_evaluation(
    *,
    live_generator: Callable[[dict[str, object], str], EmailSequenceInput] | None = None,
) -> dict[str, Any]:
    leads = build_golden_set()
    if live_generator is None:
        generator = lambda lead, version: _offline_sequence(
            lead,
            lead["brief"],
            version,
        )
        mode = "offline-deterministic"
    else:
        generator = live_generator
        mode = "live-model"

    scores: dict[str, list[dict[str, int]]] = {"v1": [], "v2": []}
    sequences: dict[tuple[int, str], EmailSequenceInput] = {}
    for version in ("v1", "v2"):
        for lead in leads:
            brief = lead["brief"]
            if not isinstance(brief, ResearchBrief):
                raise TypeError("Golden lead brief has an invalid type.")
            try:
                sequence = generator(lead, version)
                sequences[(int(lead["id"]), version)] = sequence
                scores[version].append(score_sequence(sequence, str(lead["name"]), brief))
            except Exception:
                scores[version].append(
                    {
                        "personalization": 0,
                        "faithfulness": 0,
                        "no_invented_facts": 0,
                        "length": 0,
                    }
                )

    average = {
        version: round(
            sum(sum(case.values()) for case in cases) / (len(cases) * 4),
            3,
        )
        for version, cases in scores.items()
    }
    winner = "v2" if average["v2"] >= average["v1"] else "v1"
    weakest_index = min(
        range(len(scores["v1"])),
        key=lambda index: sum(scores["v1"][index].values()),
    )
    weakest_lead = leads[weakest_index]
    before = scores["v1"][weakest_index]
    if mode == "offline-deterministic":
        improved = _offline_sequence(weakest_lead, weakest_lead["brief"], "v2")
    else:
        improved = generator(weakest_lead, "v2")
    after = score_sequence(improved, str(weakest_lead["name"]), weakest_lead["brief"])

    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "golden_leads": len(leads),
        "rubric": {
            "personalization": "5 only when both company and brief pain point are mentioned.",
            "faithfulness": "5 when the evidence guard accepts every email.",
            "no_invented_facts": "5 when evidence checks pass and no unsupported quantitative claim appears.",
            "length": "5 when each body is 12-180 words and <= 1,200 characters.",
        },
        "scores_out_of_5": {
            version: {
                metric: round(
                    sum(case[metric] for case in cases) / len(cases),
                    3,
                )
                for metric in cases[0]
            }
            for version, cases in scores.items()
        },
        "overall_average_out_of_5": average,
        "winner": winner,
        "weakest_case_improved_once": {
            "lead_id": weakest_lead["id"],
            "before": before,
            "after": after,
        },
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "latest.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    print(f"Prompt winner: {winner} (v1={average['v1']:.3f}, v2={average['v2']:.3f})")
    print(f"Weakest case before/after: {before} -> {after}")
    print(f"Report: {REPORTS_DIR / 'latest.json'}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use Gemini with fake lead data; this makes 61 free-tier API calls.",
    )
    args = parser.parse_args()
    if args.live:
        engine = get_engine()
        lead_id_by_name: dict[str, int] = {}
        with engine.begin() as connection:
            organization = connection.execute(
                models.orgs.insert()
                .values(name=f"Temporary evaluation {datetime.now(timezone.utc).isoformat()}")
                .returning(models.orgs.c.id)
            ).scalar_one()
            connection.execute(models.org_settings.insert().values(org_id=organization))
            for lead in build_golden_set():
                lead_id = connection.execute(
                    models.companies.insert().values(
                        org_id=organization,
                        name=lead["name"],
                        employees=10,
                    ).returning(models.companies.c.id)
                ).scalar_one()
                lead_id_by_name[str(lead["name"])] = int(lead_id)
        try:
            run_evaluation(
                live_generator=lambda lead, version: _live_generator(
                    lead,
                    version,
                    organization,
                    lead_id_by_name[str(lead["name"])],
                )
            )
        finally:
            with engine.begin() as connection:
                connection.execute(
                    models.orgs.delete().where(models.orgs.c.id == organization)
                )
    else:
        run_evaluation()


if __name__ == "__main__":
    main()
