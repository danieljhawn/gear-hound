import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.collectors.types import NormalizedListing
from app.models import Base, Listing, ListingState
from app.services.listing_state import (
    get_listing_first_seen,
    get_listing_states,
    set_listing_state,
    sync_listings,
)


def sample_listing(*, title: str = "Fender Fat Strat", price_cents: int = 39000):
    return NormalizedListing(
        source="craigslist",
        source_listing_id="abc123",
        title=title,
        price_cents=price_cents,
        url="https://example.test/abc123",
        location="Austin",
        source_category="musical-instruments",
        image_url="https://images.example/fender.jpg",
        raw_metadata={"category": "Guitar"},
    )


def test_listing_state_survives_listing_refreshes() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        sync_listings(session, [sample_listing()])
        set_listing_state(session, "craigslist", "abc123", "interested")
        sync_listings(session, [sample_listing(title="Fender Fat Strat - reduced", price_cents=35000)])

        states = get_listing_states(session, [sample_listing()])
        stored = session.scalar(select(Listing).where(Listing.source_listing_id == "abc123"))

        assert states[("craigslist", "abc123")] == "interested"
        assert stored is not None
        assert stored.title == "Fender Fat Strat - reduced"
        assert stored.price_cents == 35000


def test_hidden_state_is_persisted_separately_from_listing() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        sync_listings(session, [sample_listing()])
        set_listing_state(session, "craigslist", "abc123", "hidden")

        state = session.scalar(select(ListingState))
        assert state is not None
        assert state.state == "hidden"


def test_invalid_listing_state_is_rejected() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        sync_listings(session, [sample_listing()])
        with pytest.raises(ValueError, match="Unsupported listing state"):
            set_listing_state(session, "craigslist", "abc123", "deleted")


def test_get_listing_first_seen_returns_persisted_timestamp() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    listing = sample_listing()

    with Session(engine) as session:
        sync_listings(session, [listing])
        persisted = session.scalar(select(Listing))
        assert persisted is not None

        timestamps = get_listing_first_seen(session, [listing])

        assert timestamps[(listing.source, listing.source_listing_id)] == persisted.first_seen_at
