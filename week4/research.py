"""Polite public-business-site research with strict tenant and token budgets."""

import ipaddress
import re
import socket
import threading
import time
import urllib.robotparser
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Engine

from week4 import models
from week4.db import tenant_transaction
from week4.schemas import ResearchBrief
from week4.token_budget import request_budgeted
from week2.db import get_engine

USER_AGENT = "OutreachOSResearchBot/1.0"
MAX_PAGE_BYTES = 1_000_000
MAX_ROBOTS_BYTES = 64_000
MAX_TEXT_CHARS = 12_000
_last_request: dict[str, float] = {}
_rate_lock = threading.Lock()


@dataclass(frozen=True)
class FetchedWebsite:
    url: str
    text: str


class _VisibleTextParser(HTMLParser):
    """Collect readable text while ignoring scripts and other hidden markup."""

    hidden_tags = {"script", "style", "noscript", "svg", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self.hidden_tags:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.hidden_tags and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth and data.strip():
            self.parts.append(data.strip())


def extract_clean_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    text = " ".join(parser.parts)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[email removed]", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d(). -]{7,}\d)(?!\w)", "[phone removed]", text)
    return re.sub(r"\s+", " ", text)[:MAX_TEXT_CHARS].strip()


def _validate_public_host(hostname: str, port: int) -> None:
    if hostname.lower() in {"localhost", "localhost.localdomain"}:
        raise ValueError("Private and local company websites are not allowed.")
    try:
        addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as error:
        raise ValueError("The company website host could not be resolved.") from error
    if not addresses:
        raise ValueError("The company website host did not resolve to an address.")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Private and local company websites are not allowed.")


def _validate_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("A public HTTP or HTTPS company website URL is required.")
    if parsed.username or parsed.password:
        raise ValueError("Website URLs must not contain embedded credentials.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    _validate_public_host(parsed.hostname, port)
    return parsed.hostname.lower(), port


def _wait_for_domain(hostname: str) -> None:
    with _rate_lock:
        now = time.monotonic()
        delay = 1.0 - (now - _last_request.get(hostname, 0.0))
        if delay > 0:
            time.sleep(delay)
        _last_request[hostname] = time.monotonic()


def _read_response(
    client: httpx.Client,
    url: str,
    max_bytes: int,
) -> tuple[int, str, bytes]:
    with client.stream(
        "GET",
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain,*/*;q=0.1"},
        timeout=10,
        follow_redirects=False,
    ) as response:
        declared_size = response.headers.get("content-length")
        if declared_size and int(declared_size) > max_bytes:
            raise ValueError("The website response exceeds the allowed size.")
        data = bytearray()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > max_bytes:
                raise ValueError("The website response exceeds the allowed size.")
        return response.status_code, response.headers.get("content-type", ""), bytes(data)


def fetch_company_website(
    url: str,
    *,
    client: httpx.Client | None = None,
) -> FetchedWebsite:
    hostname, _ = _validate_url(url)
    own_client = client is None
    http_client = client or httpx.Client(timeout=10, follow_redirects=False)
    try:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{origin}/robots.txt"
        _wait_for_domain(hostname)
        robots_status, _, robots_bytes = _read_response(
            http_client,
            robots_url,
            MAX_ROBOTS_BYTES,
        )
        if robots_status == 404:
            robots_text = ""
        elif robots_status != 200:
            raise ValueError(f"robots.txt returned HTTP {robots_status}; fetch denied.")
        else:
            robots_text = robots_bytes.decode("utf-8", errors="replace")
        rules = urllib.robotparser.RobotFileParser()
        rules.set_url(robots_url)
        rules.parse(robots_text.splitlines())
        if not rules.can_fetch(USER_AGENT, url):
            raise ValueError("robots.txt disallows fetching this company website.")

        _wait_for_domain(hostname)
        page_status, content_type, page_bytes = _read_response(
            http_client,
            url,
            MAX_PAGE_BYTES,
        )
        if page_status != 200:
            raise ValueError(f"The company website returned HTTP {page_status}.")
        if "html" not in content_type.lower() and "xhtml" not in content_type.lower():
            raise ValueError("The company website did not return HTML.")
        clean_text = extract_clean_text(page_bytes.decode("utf-8", errors="replace"))
        if not clean_text:
            raise ValueError("No readable business text was found on the website.")
        return FetchedWebsite(url=url, text=clean_text)
    finally:
        if own_client:
            http_client.close()


def research_lead(
    org_id: int,
    lead_id: int,
    *,
    engine: Engine | None = None,
    fetcher: Callable[[str], FetchedWebsite] = fetch_company_website,
    generator: Callable[..., tuple[ResearchBrief, int, int]] | None = None,
) -> dict[str, object]:
    database = engine or get_engine()
    with tenant_transaction(org_id, engine=database) as connection:
        lead = connection.execute(
            text(
                "SELECT id, name, website FROM companies "
                "WHERE id = :lead_id AND org_id = :org_id"
            ),
            {"lead_id": lead_id, "org_id": org_id},
        ).mappings().first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    if not lead["website"]:
        raise HTTPException(status_code=422, detail="Add a public company website before research.")

    website = fetcher(lead["website"])
    prompt = (
        "Create a factual B2B company research brief. Use only the fetched public page text "
        "below. Do not infer or invent company facts, people, contact details, dates, or "
        "metrics. If evidence for a field is missing, write 'unknown'. Focus only on the "
        "business, not individuals. sources must contain only the exact fetched URL. Return "
        "JSON with pain_points (array), trigger, best_angle, confidence (0 to 1), and sources.\n"
        f"Company: {lead['name']}\nFetched URL: {website.url}\n"
        f"Public page text:\n{website.text}"
    )
    brief, input_tokens, output_tokens = request_budgeted(
        prompt,
        ResearchBrief,
        org_id=org_id,
        lead_id=lead_id,
        purpose="lead_research",
        engine=database,
        generator=generator or request_validated,
    )
    if any(source != website.url for source in brief.sources):
        raise ValueError("The research model cited a URL that was not fetched.")

    summary = (
        f"Pain points: {'; '.join(brief.pain_points)}. "
        f"Trigger: {brief.trigger}. Best angle: {brief.best_angle}."
    )
    with tenant_transaction(org_id, engine=database) as connection:
        connection.execute(
            models.lead_research.insert().values(
                org_id=org_id,
                company_id=lead_id,
                summary=summary,
                confidence=brief.confidence,
                pain_points=brief.pain_points,
                trigger=brief.trigger,
                best_angle=brief.best_angle,
                sources=brief.sources,
            )
        )
    return brief.model_dump()
