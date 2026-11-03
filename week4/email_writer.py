"""Email sequence generation and deterministic content-safety checks."""

import re
import json
from pathlib import Path
from typing import Callable, Iterable

from sqlalchemy.engine import Engine
from sqlalchemy import text

from week1.llm import request_validated
from week4 import models
from week4.db import tenant_transaction
from week4.token_budget import request_budgeted
from week4.schemas import EmailSequenceInput, ResearchBrief

PROMPTS_DIR = Path(__file__).parent / "prompts"


def validate_email_sequence(
    sequence: EmailSequenceInput,
    brief: ResearchBrief,
    company_name: str,
    banned_phrases: Iterable[str],
) -> None:
    evidence = " ".join(
        [
            company_name,
            *brief.pain_points,
            brief.trigger,
            brief.best_angle,
            *brief.sources,
        ]
    ).casefold()
    banned = [phrase.strip().casefold() for phrase in banned_phrases if phrase.strip()]
    for email in sequence.emails:
        content = f"{email.subject}\n{email.body}"
        normalized = content.casefold()
        if any(phrase in normalized for phrase in banned):
            raise ValueError("An email contains a phrase banned by organization settings.")
        if re.search(r"<\s*[/!]?[a-z][^>]*>", content, re.IGNORECASE):
            raise ValueError("Emails must be plain text, not HTML.")
        for number in re.findall(r"(?<!\w)\d[\d,.%]*(?!\w)", content):
            if number.casefold() not in evidence:
                raise ValueError(f"An email contains an unsupported numeric claim: {number}")
        # Named entities often contain capitalized words; require those beyond sentence
        # starts to appear in the lead or the approved research evidence.
        proper_nouns = []
        for match in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", email.body):
            preceding = email.body[: match.start()].rstrip()
            if preceding and not preceding.endswith((".", "!", "?", "\n")):
                proper_nouns.append(match.group())
        unsupported = [
            phrase
            for phrase in proper_nouns
            if phrase.casefold() not in evidence
            and phrase not in {"I", "We", "Your", "The", "This", "Our"}
        ]
        if unsupported:
            raise ValueError("An email contains a named entity not found in the research brief.")


def generate_sequence(
    *,
    org_id: int,
    lead_id: int,
    company_name: str,
    brief: ResearchBrief,
    tone: str,
    sample_emails: list[str],
    banned_phrases: list[str],
    prompt_version: str = "v2",
    engine: Engine | None = None,
    generator: Callable[..., tuple[EmailSequenceInput, int, int]] | None = None,
) -> tuple[EmailSequenceInput, int, int]:
    if prompt_version not in {"v1", "v2"}:
        raise ValueError("Unsupported email prompt version.")
    template = (PROMPTS_DIR / f"writer_{prompt_version}.txt").read_text(encoding="utf-8")
    prompt = (
        f"{template}\n\nBrand tone: {tone}\n"
        f"Approved sample emails: {sample_emails}\n"
        f"Banned phrases: {banned_phrases}\n"
        f"Company: {company_name}\nResearch brief: {brief.model_dump_json()}"
    )
    sequence, input_tokens, output_tokens = request_budgeted(
        prompt,
        EmailSequenceInput,
        org_id=org_id,
        lead_id=lead_id,
        purpose="email_writing",
        engine=engine,
        generator=generator or request_validated,
    )
    validate_email_sequence(sequence, brief, company_name, banned_phrases)
    return sequence, input_tokens, output_tokens


def create_and_save_sequence(
    org_id: int,
    lead_id: int,
    *,
    engine: Engine,
    prompt_version: str = "v2",
) -> dict[str, object]:
    with tenant_transaction(org_id, engine=engine) as connection:
        lead = connection.execute(
            text("SELECT id, name FROM companies WHERE id = :lead_id AND org_id = :org_id"),
            {"lead_id": lead_id, "org_id": org_id},
        ).mappings().first()
        if lead is None:
            raise ValueError("Lead not found.")
        row = connection.execute(
            text(
                "SELECT pain_points, trigger, best_angle, confidence, sources "
                "FROM lead_research WHERE org_id = :org_id AND company_id = :lead_id "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"org_id": org_id, "lead_id": lead_id},
        ).mappings().first()
        if row is None:
            raise ValueError("Research this lead before writing email.")
        settings = connection.execute(
            text(
                "SELECT tone, sample_emails, banned_phrases FROM org_settings "
                "WHERE org_id = :org_id"
            ),
            {"org_id": org_id},
        ).mappings().first()
        if settings is None:
            raise ValueError("Organization settings not found.")

    def decode_json(value: object) -> object:
        return json.loads(value) if isinstance(value, str) else value

    brief = ResearchBrief(
        pain_points=decode_json(row["pain_points"]),
        trigger=row["trigger"],
        best_angle=row["best_angle"],
        confidence=row["confidence"],
        sources=decode_json(row["sources"]),
    )
    sample_emails = decode_json(settings["sample_emails"])
    banned_phrases = decode_json(settings["banned_phrases"])
    sequence, input_tokens, output_tokens = generate_sequence(
        org_id=org_id,
        lead_id=lead_id,
        company_name=lead["name"],
        brief=brief,
        tone=settings["tone"],
        sample_emails=sample_emails,
        banned_phrases=banned_phrases,
        prompt_version=prompt_version,
        engine=engine,
    )
    with tenant_transaction(org_id, engine=engine) as connection:
        result = connection.execute(
            models.email_sequences.insert().values(
                org_id=org_id,
                lead_id=lead_id,
                status="draft",
                prompt_version=prompt_version,
            )
        )
        sequence_id = int(result.inserted_primary_key[0])
        for position, email in enumerate(sequence.emails, start=1):
            connection.execute(
                models.email_drafts.insert().values(
                    org_id=org_id,
                    sequence_id=sequence_id,
                    position=position,
                    subject=email.subject,
                    body=email.body,
                    send_delay_days=email.send_delay_days,
                    status="draft",
                )
            )
    return {
        "id": sequence_id,
        "lead_id": lead_id,
        "status": "draft",
        "prompt_version": prompt_version,
        "emails": [email.model_dump() for email in sequence.emails],
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": 0.0,
    }
