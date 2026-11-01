# Week 3 Day 4: Pydantic schemas
# OutreachOS - AI sales outreach tool
# Pydantic models validate request and response data.

from datetime import datetime
from pydantic import BaseModel, Field


class LeadCreate(BaseModel):
    """Input data for creating a new lead."""
    name: str = Field(min_length=2, max_length=100)
    city: str | None = None
    employees: int = Field(ge=0, le=100000)
    has_website: bool = False


class LeadOut(BaseModel):
    """Output data for a lead, including database-generated fields."""
    id: int
    name: str
    city: str | None
    employees: int
    has_website: bool
    created_at: datetime