from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, TypedDict

from app.collectors.types import NormalizedListing


class ListingCard(TypedDict):
    listing: NormalizedListing
    state: str
    first_seen_at: datetime | None


@dataclass(frozen=True, slots=True)
class ListingFilters:
    q: str = ""
    min_price: int | None = None
    max_price: int | None = None
    age_days: int | None = None
    source: str = "all"
    category: str = "all"
    state: str = "all"
    sort: Literal["newest", "oldest", "price_asc", "price_desc", "title"] = "newest"


def filter_and_sort_cards(
    cards: list[ListingCard], filters: ListingFilters, *, now: datetime | None = None
) -> list[ListingCard]:
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=filters.age_days) if filters.age_days is not None else None
    query_terms = filters.q.casefold().split()
    filtered: list[ListingCard] = []
    for card in cards:
        listing = card["listing"]
        searchable = f"{listing.title} {listing.location or ''}".casefold()
        if query_terms and not all(term in searchable for term in query_terms):
            continue
        if filters.min_price is not None and (
            listing.price_cents is None or listing.price_cents < filters.min_price * 100
        ):
            continue
        if (
            filters.max_price is not None
            and listing.price_cents is not None
            and listing.price_cents > filters.max_price * 100
        ):
            continue
        if filters.source != "all" and listing.source != filters.source:
            continue
        category = str(listing.raw_metadata.get("category") or "Other/Oddball")
        if filters.category != "all" and category != filters.category:
            continue
        if filters.state != "all" and card["state"] != filters.state:
            continue
        first_seen_at = card["first_seen_at"]
        if cutoff is not None:
            if first_seen_at is None:
                continue
            if first_seen_at.tzinfo is None:
                first_seen_at = first_seen_at.replace(tzinfo=UTC)
            if first_seen_at < cutoff:
                continue
        filtered.append(card)

    def seen_timestamp(card: ListingCard) -> float:
        seen = card["first_seen_at"]
        if seen is None:
            return 0
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=UTC)
        return seen.timestamp()

    if filters.sort == "oldest":
        filtered.sort(key=lambda card: (card["first_seen_at"] is None, seen_timestamp(card)))
    elif filters.sort == "price_asc":
        filtered.sort(
            key=lambda card: (
                card["listing"].price_cents is None,
                card["listing"].price_cents or 0,
            )
        )
    elif filters.sort == "price_desc":
        filtered.sort(
            key=lambda card: (
                card["listing"].price_cents is None,
                -(card["listing"].price_cents or 0),
            )
        )
    elif filters.sort == "title":
        filtered.sort(key=lambda card: card["listing"].title.casefold())
    else:
        filtered.sort(key=lambda card: (card["first_seen_at"] is None, -seen_timestamp(card)))
    return filtered
