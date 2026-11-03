import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from week4 import models
from week4.research import (
    FetchedWebsite,
    extract_clean_text,
    fetch_company_website,
    research_lead,
)
from week4.schemas import ResearchBrief


def _database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(models.orgs.insert().values(id=1, name="Research Org"))
        connection.execute(models.org_settings.insert().values(org_id=1))
        connection.execute(
            models.companies.insert().values(
                org_id=1,
                name="Example Manufacturing",
                employees=12,
                website="https://public.example/about",
                has_website=True,
            )
        )
    return engine


def test_extract_clean_text_removes_scripts_emails_and_phone_numbers() -> None:
    result = extract_clean_text(
        "<h1>Company facts</h1><script>hidden secret</script>"
        "<p>contact team@example.com at +1 (555) 123-4567</p>"
    )
    assert "Company facts" in result
    assert "hidden secret" not in result
    assert "team@example.com" not in result
    assert "123-4567" not in result


def test_fetch_obeys_robots_disallow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "week4.research.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("93.184.216.34", 0))],
    )
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            text="User-agent: *\nDisallow: /",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="robots.txt disallows"):
        fetch_company_website("https://public.example/about", client=client)
    assert requests == ["https://public.example/robots.txt"]
    client.close()


def test_research_saves_validated_brief_and_usage() -> None:
    engine = _database()
    brief = ResearchBrief(
        pain_points=["Manual production planning"],
        trigger="unknown",
        best_angle="Planning workflow automation",
        confidence=0.8,
        sources=["https://public.example/about"],
    )

    def fetcher(url: str) -> FetchedWebsite:
        return FetchedWebsite(url=url, text="Business text from a public company site.")

    def generator(*_args, **_kwargs):
        return brief, 200, 80

    result = research_lead(
        1,
        1,
        engine=engine,
        fetcher=fetcher,
        generator=generator,
    )
    assert result["confidence"] == 0.8
    with engine.connect() as connection:
        research = connection.execute(
            text("SELECT org_id, confidence, pain_points FROM lead_research")
        ).mappings().one()
        usage = connection.execute(
            text("SELECT input_tokens, output_tokens FROM token_usage")
        ).mappings().one()
    assert research["org_id"] == 1
    assert research["confidence"] == 0.8
    assert research["pain_points"] == '["Manual production planning"]'
    assert usage == {"input_tokens": 200, "output_tokens": 80}
    engine.dispose()


def test_research_rejects_brief_sources_not_fetched() -> None:
    engine = _database()
    brief = ResearchBrief(
        pain_points=["unknown"],
        trigger="unknown",
        best_angle="unknown",
        confidence=0,
        sources=["https://not-fetched.example"],
    )
    with pytest.raises(ValueError, match="URL that was not fetched"):
        research_lead(
            1,
            1,
            engine=engine,
            fetcher=lambda url: FetchedWebsite(url, "public page text"),
            generator=lambda *_args, **_kwargs: (brief, 10, 5),
        )
    engine.dispose()
