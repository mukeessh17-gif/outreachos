"""Validated API request and response models."""

import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic import model_validator


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)
    org_name: str = Field(min_length=2, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    org_id: int
    org_name: str
    user_id: int


class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    employees: int = Field(default=0, ge=0, le=1_000_000)
    has_website: bool = False
    website: str | None = Field(default=None, max_length=2_000)


class LeadPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    employees: int | None = Field(default=None, ge=0, le=1_000_000)
    has_website: bool | None = None
    website: str | None = Field(default=None, max_length=2_000)
    pipeline_stage: Literal["new", "contacted", "replied", "meeting", "closed"] | None = None


class ContactCreate(BaseModel):
    full_name: str = Field(default="", max_length=120)
    email: str = Field(min_length=3, max_length=320)
    role: str | None = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class InboxCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class SettingsUpdate(BaseModel):
    tone: str = Field(default="professional", min_length=1, max_length=80)
    sample_emails: list[str] = Field(default_factory=list, max_length=10)
    banned_phrases: list[str] = Field(default_factory=list, max_length=100)
    sender_postal_address: str = Field(default="", max_length=500)
    calendar_link: str = Field(default="", max_length=2_000)
    daily_token_budget: int = Field(default=100_000, ge=1, le=10_000_000)
    per_lead_token_budget: int = Field(default=10_000, ge=1, le=1_000_000)
    daily_lead_limit: int = Field(default=1_000, ge=1, le=100_000)

    @field_validator("calendar_link")
    @classmethod
    def validate_calendar_link(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return ""
        parsed = urlsplit(normalized)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"})
        ):
            raise ValueError("Booking link must be HTTPS (HTTP is allowed only for localhost).")
        return normalized


class ResearchBrief(BaseModel):
    pain_points: list[str] = Field(min_length=1, max_length=10)
    trigger: str = Field(min_length=1, max_length=500)
    best_angle: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0, le=1)
    sources: list[str] = Field(min_length=1, max_length=20)


class EmailDraftInput(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=1_200)
    send_delay_days: int = Field(ge=0, le=365)


class EmailSequenceInput(BaseModel):
    emails: list[EmailDraftInput] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def delays_are_in_order(self) -> "EmailSequenceInput":
        delays = [email.send_delay_days for email in self.emails]
        if delays[0] != 0 or delays != sorted(delays):
            raise ValueError("The first email must send on day 0 and later delays must increase.")
        return self


class EmailSequenceStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]


class BulkApproveRequest(BaseModel):
    sequence_ids: list[int] = Field(min_length=1, max_length=100)


class EmailDraftPatch(EmailDraftInput):
    pass


class ReplyClassification(BaseModel):
    category: Literal["interested", "objection", "unsubscribe", "out-of-office", "other"]
    confidence: float = Field(ge=0, le=1)
    draft_response: str | None = Field(default=None, max_length=2_000)


class OutboxSendRequest(BaseModel):
    draft_id: int = Field(ge=1)
    inbox_id: int = Field(ge=1)
    recipient: str = Field(min_length=3, max_length=320)

    @field_validator("recipient")
    @classmethod
    def normalize_recipient(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid recipient address.")
        return normalized


class ScheduleSequenceRequest(BaseModel):
    inbox_id: int = Field(ge=1)
    recipient: str = Field(min_length=3, max_length=320)

    @field_validator("recipient")
    @classmethod
    def normalize_recipient(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid recipient address.")
        return normalized


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    message: str = Field(min_length=5, max_length=2_000)


class ReplyRequest(BaseModel):
    lead_id: int = Field(ge=1)
    sender_email: str = Field(min_length=3, max_length=320)
    body: str = Field(min_length=1, max_length=10_000)

    @field_validator("sender_email")
    @classmethod
    def normalize_sender_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid sender email address.")
        return normalized


class CalendarBookingRequest(BaseModel):
    lead_id: int = Field(ge=1)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def booking_has_positive_duration(self) -> "CalendarBookingRequest":
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Booking times must include a timezone.")
        if self.ends_at <= self.starts_at:
            raise ValueError("Booking end must be after start.")
        return self


class FreeBusyRequest(BaseModel):
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def valid_range(self) -> "FreeBusyRequest":
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Free/busy times must include a timezone.")
        if self.ends_at <= self.starts_at:
            raise ValueError("End time must be after start time.")
        if (self.ends_at - self.starts_at).total_seconds() > 60 * 60 * 24 * 31:
            raise ValueError("Free/busy range cannot exceed 31 days.")
        return self


class PromptExperimentRequest(BaseModel):
    lead_id: int = Field(ge=1)
    version: Literal["v1", "v2"]
    outcome: Literal["sent", "replied", "meeting", "no_response", "rejected"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    org_id: int


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
