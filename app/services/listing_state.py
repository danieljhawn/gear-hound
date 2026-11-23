from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.types import NormalizedListing
from app.models import Listing, ListingState, utc_now

SUPPORTED_STATES = {"normal", "interested", "hidden"}


def sync_listings(session: Session, listings: Iterable[NormalizedListing]) -> None:
    for item in listings:
        listing = session.scalar(
            select(Listing).where(
                Listing.source == item.source,
                Listing.source_listing_id == item.source_listing_id,
            )
        )
        if listing is None:
            listing = Listing(
                source=item.source,
                source_listing_id=item.source_listing_id,
                url=item.url,
                title=item.title,
                price_cents=item.price_cents,
            )
            session.add(listing)
        listing.url = item.url
        listing.title = item.title
        listing.price_cents = item.price_cents
        listing.location = item.location
        listing.source_category = item.source_category
        listing.normalized_category = item.raw_metadata.get("category")
        listing.image_url = item.image_url
        listing.source_posted_at = item.source_posted_at
        listing.last_seen_at = utc_now()
        listing.active = True
        listing.consecutive_misses = 0
        listing.raw_metadata = item.raw_metadata
    session.commit()


def get_listing_states(
    session: Session, listings: Iterable[NormalizedListing]
) -> dict[tuple[str, str], str]:
    states: dict[tuple[str, str], str] = {}
    for item in listings:
        state = session.scalar(
            select(ListingState)
            .join(Listing, Listing.id == ListingState.listing_id)
            .where(
                Listing.source == item.source,
                Listing.source_listing_id == item.source_listing_id,
            )
        )
        states[(item.source, item.source_listing_id)] = state.state if state else "normal"
    return states


def set_listing_state(
    session: Session, source: str, source_listing_id: str, state: str
) -> None:
    if state not in SUPPORTED_STATES:
        raise ValueError(f"Unsupported listing state: {state}")
    listing = session.scalar(
        select(Listing).where(
            Listing.source == source,
            Listing.source_listing_id == source_listing_id,
        )
    )
    if listing is None:
        raise LookupError(f"Listing not found: {source}/{source_listing_id}")
    listing_state = session.scalar(
        select(ListingState).where(ListingState.listing_id == listing.id)
    )
    if listing_state is None:
        listing_state = ListingState(listing_id=listing.id)
        session.add(listing_state)
    listing_state.state = state
    session.commit()
