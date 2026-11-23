from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class NormalizedListing:
    source: str
    source_listing_id: str
    title: str
    price_cents: int | None
    url: str
    location: str | None
    source_category: str | None
    image_url: str | None
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    source_posted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CollectionResult:
    source: str
    listings: list[NormalizedListing]
    complete: bool
    error: str | None = None
