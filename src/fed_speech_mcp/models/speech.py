"""Speech data models following the V1 output format specification."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SpeakerRole(str, Enum):
    """Controlled vocabulary for speaker roles."""

    CHAIR = "Chair"
    VICE_CHAIR = "Vice Chair"
    GOVERNOR = "Governor"


class DocType(str, Enum):
    """Controlled vocabulary for document types."""

    SPEECH = "speech"
    TESTIMONY = "testimony"
    PREPARED_REMARKS = "prepared_remarks"


class ImportanceTier(str, Enum):
    """Importance tier levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Speaker(BaseModel):
    """Speaker information."""

    name: str = Field(..., description="Full name of the speaker")
    role: SpeakerRole = Field(..., description="Role of the speaker")
    organization: str = Field(
        default="Board of Governors of the Federal Reserve System",
        description="Organization the speaker represents",
    )


class Event(BaseModel):
    """Event information where the speech was given."""

    name: Optional[str] = Field(None, description="Name of the event")
    location: Optional[str] = Field(None, description="Location of the event")


class Source(BaseModel):
    """Source information for traceability."""

    publisher: str = Field(
        default="Board of Governors of the Federal Reserve System",
        description="Publisher of the document",
    )
    collection: str = Field(..., description="Collection type (speeches, testimony)")
    url: str = Field(..., description="Original source URL")
    retrieved_at: datetime = Field(..., description="When the document was retrieved")


class TextContent(BaseModel):
    """Text content of the speech."""

    raw: str = Field(..., description="Raw text with original formatting")
    clean: str = Field(..., description="Cleaned text without boilerplate")


class TopicFlags(BaseModel):
    """Topic mention flags based on keyword matching."""

    inflation: bool = Field(default=False, description="Mentions inflation topics")
    labor_market: bool = Field(default=False, description="Mentions labor market topics")
    rates: bool = Field(default=False, description="Mentions interest rate topics")
    balance_sheet: bool = Field(default=False, description="Mentions balance sheet topics")
    growth: bool = Field(default=False, description="Mentions growth topics")
    financial_stability: bool = Field(
        default=False, description="Mentions financial stability topics"
    )


class Features(BaseModel):
    """Computed features from the speech text."""

    word_count: int = Field(..., description="Total word count of clean text")
    language: str = Field(default="en", description="Language of the document")
    has_qa: bool = Field(default=False, description="Whether the speech contains Q&A section")
    topics: TopicFlags = Field(
        default_factory=TopicFlags, description="Topic mention flags"
    )


class Importance(BaseModel):
    """Rule-based importance scoring."""

    tier: ImportanceTier = Field(..., description="Importance tier: high, medium, low")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized importance score")
    reasons: list[str] = Field(
        default_factory=list, description="Explanatory reasons for the score"
    )


class Speech(BaseModel):
    """Complete speech document following V1 output format."""

    doc_id: str = Field(..., description="Unique document identifier")
    source: Source = Field(..., description="Source information")
    published_at: datetime = Field(..., description="Publication date (ISO 8601)")
    title: str = Field(..., description="Title of the speech")
    speaker: Speaker = Field(..., description="Speaker information")
    doc_type: DocType = Field(..., description="Type of document")
    event: Event = Field(default_factory=Event, description="Event information")
    text: TextContent = Field(..., description="Speech text content")
    features: Features = Field(..., description="Computed features")
    importance: Importance = Field(..., description="Importance scoring")

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

