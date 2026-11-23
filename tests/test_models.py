import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Base, Listing, ListingObservation


def test_listing_identity_is_unique_within_a_source() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Listing(
                source="craigslist",
                source_listing_id="8001021969",
                url="https://example.test/first",
                title="Oddball synth",
                price_cents=40000,
            )
        )
        session.commit()

        session.add(
            Listing(
                source="craigslist",
                source_listing_id="8001021969",
                url="https://example.test/repost",
                title="Oddball synth repost",
                price_cents=39000,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_listing_observations_preserve_price_history_and_allow_barter() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        listing = Listing(
            source="craigslist",
            source_listing_id="trade-1",
            url="https://example.test/trade",
            title="FSOT synth for bass",
            price_cents=None,
        )
        session.add(listing)
        session.flush()
        session.add_all(
            [
                ListingObservation(listing_id=listing.id, price_cents=None, available=True),
                ListingObservation(listing_id=listing.id, price_cents=35000, available=True),
            ]
        )
        session.commit()

        observations = session.query(ListingObservation).order_by(ListingObservation.id).all()

        assert [observation.price_cents for observation in observations] == [None, 35000]
        assert all(observation.listing_id == listing.id for observation in observations)
